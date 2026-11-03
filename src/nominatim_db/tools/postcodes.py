# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing, updating and otherwise maintaining the table
of artificial postcode centroids.
"""
from typing import Optional, TextIO
from collections import defaultdict
from pathlib import Path
import csv
import gzip
import logging
import json
from math import isfinite

from psycopg import sql as pysql

from ..db.connection import connect, Connection, table_exists
from ..utils.centroid import PointsCentroid
from ..data.postcode_format import PostcodeFormatter, CountryPostcodeMatcher, PostcodeMatch
from ..tokenizer.base import AbstractTokenizer

LOG = logging.getLogger()


def _to_float(numstr: str, max_value: float) -> float:
    """ Convert the number in string into a float. The number is expected
        to be in the range of [-max_value, max_value]. Otherwise rises a
        ValueError.
    """
    num = float(numstr)
    if not isfinite(num) or num <= -max_value or num >= max_value:
        raise ValueError()

    return num


def _extent_to_rank(extent: int) -> int:
    """ Guess a suitable search rank from the extent of a postcode.
    """
    if extent <= 100:
        return 25
    if extent <= 3000:
        return 23
    return 21


def _open_external_file(fname: Path) -> TextIO:
    """ Open an external postcode data file, handling both flat text
        and gzip compression transparently based on the file extension.
    """
    if fname.suffix == '.gz':
        return gzip.open(fname, 'rt', encoding='utf-8')
    return open(fname, 'r', encoding='utf-8')


class _PostcodeCollector:
    """ Collector for postcodes of a single country.
    """

    def __init__(self, country: str, matcher: Optional[CountryPostcodeMatcher],
                 exclude: set[str] = set()):
        self.country = country
        self.matcher = matcher
        self.exclude = exclude
        self.collected: dict[str, PointsCentroid] = {}
        self.normalization_cache: tuple[str, Optional[PostcodeMatch]] = ('', None)

    def add(self, postcode: str, x: float, y: float) -> None:
        """ Add the given postcode to the collection cache. If the postcode
            already existed, it is overwritten with the new centroid.
        """
        if self.matcher is not None:
            normalized: Optional[PostcodeMatch]
            if self.normalization_cache[0] == postcode:
                normalized = self.normalization_cache[1]
            else:
                normalized = self.matcher.match(postcode)
                self.normalization_cache = (postcode, normalized)

            if normalized is not None and normalized.norm not in self.exclude:
                if (c := self.collected.get(normalized.norm)):
                    c += (x, y)
                else:
                    pt = PointsCentroid(normalized.extent)
                    pt += (x, y)
                    self.collected[normalized.norm] = pt

    def commit(self, conn: Connection, project_dir: Optional[Path], is_initial: bool) -> None:
        """ Update postcodes for the country from the postcodes selected so far.

            When 'project_dir' is set, then any postcode files found in this
            directory are taken into account as well.
        """
        if project_dir is not None:
            self._update_from_external(project_dir)

        if is_initial:
            to_delete = []
        else:
            with conn.cursor() as cur:
                # Ensure we only drop non-area artificial points on point updates
                cur.execute("""SELECT postcode FROM location_postcodes
                               WHERE country_code = %s AND osm_id IS NULL AND NOT is_area""",
                            (self.country, ))
                to_delete = [row[0] for row in cur if row[0] not in self.collected]

        to_add = [dict(zip(('pc', 'rank', 'extent', 'x', 'y'),
                           (k, _extent_to_rank(v.extent), v.extent, *v.centroid())))
                  for k, v in self.collected.items()]
        self.collected = {}

        LOG.info("Processing country '%s' (%s added, %s deleted).",
                 self.country, len(to_add), len(to_delete))

        with conn.cursor() as cur:
            if to_add:
                columns = ['country_code',
                           'rank_search',
                           'postcode',
                           'centroid',
                           'geometry']
                values = [pysql.Literal(self.country),
                          pysql.Placeholder('rank'),
                          pysql.Placeholder('pc'),
                          pysql.SQL('ST_SetSRID(ST_MakePoint(%(x)s, %(y)s), 4326)'),
                          pysql.SQL("""expand_by_meters(
                                           ST_SetSRID(ST_MakePoint(%(x)s, %(y)s), 4326),
                                                      %(extent)s)""")]
                if is_initial:
                    columns.extend(('place_id', 'indexed_status'))
                    values.extend((pysql.SQL("nextval('seq_place')"), pysql.Literal(1)))

                cur.executemany(pysql.SQL("INSERT INTO location_postcodes ({}) VALUES ({})")
                                     .format(pysql.SQL(',')
                                                  .join(pysql.Identifier(c) for c in columns),
                                             pysql.SQL(',').join(values)),
                                to_add)
            if to_delete:
                cur.execute("""DELETE FROM location_postcodes
                               WHERE country_code = %s and postcode = any(%s)
                                     AND osm_id is null and not is_area
                            """, (self.country, to_delete))

    def _update_from_external(self, project_dir: Path) -> None:
        """ Look for an external postcode file for the active country in
            the project directory and add missing postcodes when found.
        """
        fname = self._find_external_centroid_file(project_dir)
        if fname is None or self.matcher is None:
            return

        with _open_external_file(fname) as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'postcode' not in row or 'lat' not in row or 'lon' not in row:
                    LOG.warning("Bad format for external postcode file for country '%s'."
                                " Ignored.", self.country)
                    return
                if (m := self.matcher.match(row['postcode'])):
                    if m.norm not in self.collected and m.norm not in self.exclude:
                        try:
                            # Do float conversation separately, it might throw
                            centroid = (_to_float(row['lon'], 180),
                                        _to_float(row['lat'], 90))
                            coll = PointsCentroid(m.extent)
                            coll += centroid
                            self.collected[m.norm] = coll
                        except ValueError:
                            LOG.warning("Bad coordinates %s, %s in '%s' country postcode file.",
                                        row['lat'], row['lon'], self.country)
                else:
                    LOG.warning("Badly formatted postcode '%s' in file for country '%s'. Ignored.",
                                row['postcode'], self.country)

    def _find_external_centroid_file(self, project_dir: Path) -> Optional[Path]:
        for ext in ('csv', 'csv.gz'):
            fname = project_dir / f'{self.country}_postcodes.{ext}'
            if fname.is_file():
                LOG.info("Using external postcode file '%s'.", fname)
                return fname
        return None


def update_postcodes(dsn: str, project_dir: Optional[Path],
                     tokenizer: AbstractTokenizer, force_reimport: bool = False) -> None:
    """ Update the table of postcodes from the input tables
        placex and place_postcode.
    """
    matcher = PostcodeFormatter()
    with connect(dsn) as conn:
        # Backfill country_code column where required
        conn.execute("""UPDATE place_postcode
                          SET country_code = get_country_code(centroid)
                          WHERE country_code is null
                     """)
        if force_reimport:
            conn.execute("TRUNCATE location_postcodes")
            is_initial = True
        else:
            is_initial = _is_postcode_table_empty(conn)
        if is_initial:
            conn.execute("""ALTER TABLE location_postcodes
                            DISABLE TRIGGER location_postcodes_before_insert""")
        # Now update first postcode areas
        _update_postcode_areas(conn, matcher, is_initial)
        # Update postcode areas from external geometry files
        _update_external_postcode_areas(conn, matcher, project_dir, is_initial)
        # Then fill with estimated postcode centroids from other info
        _update_guessed_postcode(conn, matcher, project_dir, is_initial)
        if is_initial:
            conn.execute("""ALTER TABLE location_postcodes
                            ENABLE TRIGGER location_postcodes_before_insert""")
        conn.commit()

    with tokenizer.name_analyzer() as analyzer:
        analyzer.update_postcodes_from_db()


def _is_postcode_table_empty(conn: Connection) -> bool:
    """ Check if there are any entries in the location_postcodes table yet.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT place_id FROM location_postcodes LIMIT 1")
        return cur.fetchone() is None


def _insert_postcode_areas(conn: Connection, country_code: str,
                           pcs: list[dict[str, str]], is_initial: bool) -> None:
    if pcs:
        with conn.cursor() as cur:
            columns = ['osm_id', 'country_code',
                       'rank_search', 'postcode', 'is_area',
                       'centroid', 'geometry']
            values = [pysql.Identifier('osm_id'), pysql.Identifier('country_code'),
                      pysql.Placeholder('rank'), pysql.Placeholder('out'),
                      pysql.Literal(True), pysql.Identifier('centroid'),
                      pysql.Identifier('geometry')]
            if is_initial:
                columns.extend(('place_id', 'indexed_status'))
                values.extend((pysql.SQL("nextval('seq_place')"), pysql.Literal(1)))

            cur.executemany(
                pysql.SQL(
                    """ INSERT INTO location_postcodes ({})
                            SELECT {} FROM place_postcode
                            WHERE osm_type = 'R'
                                  and country_code = {} and postcode = %(in)s
                                  and geometry is not null
                    """).format(pysql.SQL(',')
                                     .join(pysql.Identifier(c) for c in columns),
                                pysql.SQL(',').join(values),
                                pysql.Literal(country_code)),
                pcs)


def _update_postcode_areas(conn: Connection, matcher: PostcodeFormatter,
                           is_initial: bool) -> None:
    """ Update the postcode areas made from postcode boundaries.
    """
    # first delete all areas that have gone
    if not is_initial:
        conn.execute(""" DELETE FROM location_postcodes pc
                         WHERE pc.osm_id is not null
                           AND NOT EXISTS(
                                  SELECT * FROM place_postcode pp
                                  WHERE pp.osm_type = 'R' and pp.osm_id = pc.osm_id
                                        and geometry is not null)
                    """)
    # now insert all in country batches, triggers will ensure proper updates
    with conn.cursor() as cur:
        cur.execute(""" SELECT country_code, postcode FROM place_postcode
                        WHERE geometry is not null and osm_type = 'R'
                        ORDER BY country_code
                    """)
        country_code = None
        fmt = None
        pcs = []
        for cc, postcode in cur:
            if country_code is None:
                country_code = cc
                fmt = matcher.get_matcher(country_code)
            elif country_code != cc:
                _insert_postcode_areas(conn, country_code, pcs, is_initial)
                country_code = cc
                fmt = matcher.get_matcher(country_code)
                pcs = []

            if fmt is not None:
                if (m := fmt.match(postcode)):
                    pcs.append({'out': m.norm, 'in': postcode, 'rank': _extent_to_rank(m.extent)})

        if country_code is not None and pcs:
            _insert_postcode_areas(conn, country_code, pcs, is_initial)


def _find_external_geometry_file(project_dir: Path, country: str) -> Optional[Path]:
    for ext in ('jsonl', 'jsonl.gz'):
        fname = project_dir / f'{country}_postcodes_geometry.{ext}'
        if fname.is_file():
            LOG.info("Using external postcode file '%s'.", fname)
            return fname
    return None


def _insert_external_postcode_areas(conn: Connection, country_code: str,
                                    pcs: list[dict[str, Optional[str | float]]],
                                    is_initial: bool) -> None:
    if not pcs:
        return

    if not is_initial:
        # first get the list of existing postcodes from previous geometry import.
        with conn.cursor() as cur:
            cur.execute("""SELECT postcode FROM location_postcodes
                            WHERE country_code = %s AND osm_id IS NULL AND is_area""",
                        (country_code,))
            existing_pcs = {row[0] for row in cur}

        new_pcs = {p['postcode'] for p in pcs}

        # Delete postcodes that were previously imported but no longer appear
        to_delete = existing_pcs - new_pcs

        if to_delete:
            with conn.cursor() as cur:
                cur.execute("""DELETE FROM location_postcodes
                            WHERE country_code = %s AND osm_id IS NULL AND is_area
                            AND postcode = any(%s)
                            """, (country_code, list(to_delete)))

    with conn.cursor() as cur:
        columns = ['country_code', 'rank_search', 'postcode',
                   'is_area', 'centroid', 'geometry']
        values = [
            pysql.Literal(country_code),
            pysql.Placeholder('rank'),
            pysql.Placeholder('postcode'),
            pysql.Literal(True),
            pysql.SQL("""COALESCE(
                           ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326),
                           ST_Centroid(ST_GeomFromGeoJSON(%(geometry)s))
                         )"""),
            pysql.SQL("ST_GeomFromGeoJSON(%(geometry)s)"),
        ]
        if is_initial:
            columns.extend(('place_id', 'indexed_status'))
            values.extend((pysql.SQL("nextval('seq_place')"), pysql.Literal(1)))

        cur.executemany(
            pysql.SQL("INSERT INTO location_postcodes ({}) VALUES ({})").format(
                pysql.SQL(',').join(pysql.Identifier(c) for c in columns),
                pysql.SQL(',').join(values)
            ),
            pcs
        )


def _update_external_postcode_areas(conn: Connection, matcher: PostcodeFormatter,
                                    project_dir: Optional[Path], is_initial: bool) -> None:
    if project_dir is None:
        return

    with conn.cursor() as cur:
        cur.execute("SELECT country_code FROM country_name")
        todo_countries = {row[0] for row in cur}

    # Exclude postcodes that are already covered by OSM areas.
    area_pcs: dict[str, set[str]] = defaultdict(set)
    with conn.cursor() as cur:
        cur.execute("""SELECT country_code, postcode FROM location_postcodes
                       WHERE is_area = true AND osm_id IS NOT NULL""")
        for cc, pc in cur:
            area_pcs[cc].add(pc)

    for country in todo_countries:
        fmt = matcher.get_matcher(country)
        if fmt is None:
            continue

        fname = _find_external_geometry_file(project_dir, country)
        if fname is None:
            continue

        pcs: list[dict[str, Optional[str | float]]] = []
        with _open_external_file(fname) as jsonlfile:
            for i, line in enumerate(jsonlfile, start=1):
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    LOG.warning("Ignored line %s: bad JSON for country '%s'.", i, country)
                    continue

                geometry = data.get('geometry')
                if (not isinstance(geometry, dict) or
                        geometry.get('type') not in ('Polygon', 'MultiPolygon') or
                        not isinstance(geometry.get('coordinates'), list)):
                    LOG.warning("Ignored line %s: bad geometry for country '%s'.", i, country)
                    continue

                props = data.get('properties')
                if not isinstance(props, dict):
                    LOG.warning("Ignored line %s: bad properties for country '%s'.", i, country)
                    continue

                raw_postcode = props.get('postcode')
                if not raw_postcode:
                    LOG.warning("Ignored line %s: missing postcode for country '%s'.", i, country)
                    continue

                m = fmt.match(raw_postcode)
                if not m:
                    LOG.warning("Ignored line %s: badly formatted postcode for country '%s'.",
                                i, country)
                    continue

                if m.norm in area_pcs[country]:
                    continue

                # parse optional centroid
                lon, lat = None, None
                if props.get('lon') is not None and props.get('lat') is not None:
                    try:
                        lat = _to_float(props['lat'], 90)
                        lon = _to_float(props['lon'], 180)
                    except ValueError:
                        LOG.warning("Bad centroid on line %s for country '%s', "
                                    "will use geometry centroid.", i, country)
                        lat, lon = None, None

                pcs.append({
                    'postcode': m.norm,
                    'geometry': json.dumps(geometry),
                    'rank': _extent_to_rank(m.extent),
                    'lon': lon,
                    'lat': lat,
                })

        _insert_external_postcode_areas(conn, country, pcs, is_initial)


def _update_guessed_postcode(conn: Connection, matcher: PostcodeFormatter,
                             project_dir: Optional[Path], is_initial: bool) -> None:
    """ Computes artificial postcode centroids from the placex table,
        potentially enhances it with external postcode centroid data and then updates
        the postcodes in the table 'location_postcodes'.
    """
    # First get the list of countries that currently have postcodes.
    # (Doing this before starting to insert, so it is fast on import.)
    if is_initial:
        todo_countries: set[str] = set()
    else:
        with conn.cursor() as cur:
            cur.execute("""SELECT DISTINCT country_code FROM location_postcodes
                            WHERE osm_id is null AND not is_area""")
            todo_countries = {row[0] for row in cur}

    # Next, get the list of postcodes already covered by areas (both OSM and geometry import).
    area_pcs = defaultdict(set)
    with conn.cursor() as cur:
        cur.execute("""SELECT country_code, postcode
                       FROM location_postcodes WHERE is_area
                       ORDER BY country_code""")
        for cc, pc in cur:
            area_pcs[cc].add(pc)

    # Create a temporary table which contains coverage of the postcode areas imported from osm
    # and external geometry imported through xx_postcode_areas.jsonl.
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS _global_postcode_area")
        cur.execute("""CREATE TABLE _global_postcode_area AS
                       (SELECT ST_SubDivide(ST_SimplifyPreserveTopology(
                                              ST_Union(geometry), 0.00001), 128) as geometry
                        FROM location_postcodes WHERE is_area)
                    """)
        cur.execute("CREATE INDEX ON _global_postcode_area USING gist(geometry)")

    # Recompute the list of valid postcodes from placex.
    with conn.cursor(name="placex_postcodes") as cur:
        cur.execute("""
            SELECT country_code, postcode, ST_X(centroid), ST_Y(centroid)
              FROM (
                (SELECT country_code, address->'postcode' as postcode, centroid
                  FROM placex WHERE address ? 'postcode')
                UNION
                (SELECT country_code, postcode, centroid
                 FROM place_postcode WHERE geometry is null)
              ) x
              WHERE not postcode like '%,%' and not postcode like '%;%'
                    AND NOT EXISTS(SELECT * FROM _global_postcode_area g
                                   WHERE ST_Intersects(x.centroid, g.geometry))
              ORDER BY country_code""")

        collector = None

        for country, postcode, x, y in cur:
            if collector is None or country != collector.country:
                if collector is not None:
                    collector.commit(conn, project_dir, is_initial)
                collector = _PostcodeCollector(country, matcher.get_matcher(country),
                                               exclude=area_pcs[country])
                todo_countries.discard(country)
            collector.add(postcode, x, y)

        if collector is not None:
            collector.commit(conn, project_dir, is_initial)

    # Now handle any countries that are only in the postcode table.
    for country in todo_countries:
        fmt = matcher.get_matcher(country)
        _PostcodeCollector(country, fmt,
                           exclude=area_pcs[country]).commit(conn, project_dir, False)

    conn.execute("DROP TABLE IF EXISTS _global_postcode_area")


def can_compute(dsn: str) -> bool:
    """ Check that the necessary tables exist so that postcodes can be computed.
    """
    with connect(dsn) as conn:
        return table_exists(conn, 'place_postcode')
