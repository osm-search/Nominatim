# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing, updating and otherwise maintaining the table
of artificial postcode centroids.
"""
from typing import Optional, Tuple, Dict, TextIO
from collections import defaultdict
from pathlib import Path
import csv
import gzip
import logging
from math import isfinite

from psycopg import sql as pysql

from ..db.connection import connect, Connection, table_exists
from ..utils.centroid import PointsCentroid
from ..data.postcode_format import PostcodeFormatter, CountryPostcodeMatcher
from ..tokenizer.base import AbstractAnalyzer, AbstractTokenizer

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


class _PostcodeCollector:
    """ Collector for postcodes of a single country.
    """

    def __init__(self, country: str, matcher: Optional[CountryPostcodeMatcher],
                 default_extent: int, exclude: set[str] = set()):
        self.country = country
        self.matcher = matcher
        self.extent = default_extent
        self.exclude = exclude
        self.collected: Dict[str, PointsCentroid] = defaultdict(PointsCentroid)
        self.normalization_cache: Optional[Tuple[str, Optional[str]]] = None

    def add(self, postcode: str, x: float, y: float) -> None:
        """ Add the given postcode to the collection cache. If the postcode
            already existed, it is overwritten with the new centroid.
        """
        if self.matcher is not None:
            normalized: Optional[str]
            if self.normalization_cache and self.normalization_cache[0] == postcode:
                normalized = self.normalization_cache[1]
            else:
                match = self.matcher.match(postcode)
                normalized = self.matcher.normalize(match) if match else None
                self.normalization_cache = (postcode, normalized)

            if normalized and normalized not in self.exclude:
                self.collected[normalized] += (x, y)

    def commit(self, conn: Connection, analyzer: AbstractAnalyzer,
               project_dir: Optional[Path]) -> None:
        """ Update postcodes for the country from the postcodes selected so far.

            When 'project_dir' is set, then any postcode files found in this
            directory are taken into account as well.
        """
        if project_dir is not None:
            self._update_from_external(analyzer, project_dir)

        with conn.cursor() as cur:
            cur.execute("""SELECT postcode FROM location_postcodes
                           WHERE country_code = %s AND osm_id is null""",
                        (self.country, ))
            to_delete = [row[0] for row in cur if row[0] not in self.collected]

        to_add = [dict(zip(('pc', 'x', 'y'), (k, *v.centroid())))
                  for k, v in self.collected.items()]
        self.collected = defaultdict(PointsCentroid)

        LOG.info("Processing country '%s' (%s added, %s deleted).",
                 self.country, len(to_add), len(to_delete))

        with conn.cursor() as cur:
            if to_add:
                cur.executemany(pysql.SQL(
                    """INSERT INTO location_postcodes
                         (country_code, rank_search, postcode, centroid, geometry)
                       VALUES ({}, {}, %(pc)s,
                               ST_SetSRID(ST_MakePoint(%(x)s, %(y)s), 4326),
                               expand_by_meters(ST_SetSRID(ST_MakePoint(%(x)s, %(y)s), 4326), {}))
                    """).format(pysql.Literal(self.country),
                                pysql.Literal(_extent_to_rank(self.extent)),
                                pysql.Literal(self.extent)),
                    to_add)
            if to_delete:
                cur.execute("""DELETE FROM location_postcodes
                               WHERE country_code = %s and postcode = any(%s)
                                     AND osm_id is null
                            """, (self.country, to_delete))

    def _update_from_external(self, analyzer: AbstractAnalyzer, project_dir: Path) -> None:
        """ Look for an external postcode file for the active country in
            the project directory and add missing postcodes when found.
        """
        csvfile = self._open_external(project_dir)
        if csvfile is None:
            return

        try:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'postcode' not in row or 'lat' not in row or 'lon' not in row:
                    LOG.warning("Bad format for external postcode file for country '%s'."
                                " Ignored.", self.country)
                    return
                postcode = analyzer.normalize_postcode(row['postcode'])
                if postcode not in self.collected:
                    try:
                        # Do float conversation separately, it might throw
                        centroid = (_to_float(row['lon'], 180),
                                    _to_float(row['lat'], 90))
                        self.collected[postcode] += centroid
                    except ValueError:
                        LOG.warning("Bad coordinates %s, %s in '%s' country postcode file.",
                                    row['lat'], row['lon'], self.country)

        finally:
            csvfile.close()

    def _open_external(self, project_dir: Path) -> Optional[TextIO]:
        fname = project_dir / f'{self.country}_postcodes.csv'

        if fname.is_file():
            LOG.info("Using external postcode file '%s'.", fname)
            return open(fname, 'r', encoding='utf-8')

        fname = project_dir / f'{self.country}_postcodes.csv.gz'

        if fname.is_file():
            LOG.info("Using external postcode file '%s'.", fname)
            return gzip.open(fname, 'rt')

        return None


def update_postcodes(dsn: str, project_dir: Optional[Path], tokenizer: AbstractTokenizer) -> None:
    """ Update the table of postcodes from the input tables
        placex and place_postcode.
    """
    matcher = PostcodeFormatter()
    with tokenizer.name_analyzer() as analyzer:
        with connect(dsn) as conn:
            # Backfill country_code column where required
            conn.execute("""UPDATE place_postcode
                              SET country_code = get_country_code(centroid)
                              WHERE country_code is null
                         """)
            # Now update first postcode areas
            _update_postcode_areas(conn, analyzer, matcher)
            # Then fill with estimated postcode centroids from other info
            _update_guessed_postcode(conn, analyzer, matcher, project_dir)
            conn.commit()

        analyzer.update_postcodes_from_db()


def _insert_postcode_areas(conn: Connection, country_code: str,
                           extent: int, pcs: list[dict[str, str]]) -> None:
    if pcs:
        with conn.cursor() as cur:
            cur.executemany(
                pysql.SQL(
                    """ INSERT INTO location_postcodes
                            (osm_id, country_code, rank_search, postcode, centroid, geometry)
                            SELECT osm_id, country_code, {}, %(out)s, centroid, geometry
                            FROM place_postcode
                            WHERE osm_type = 'R'
                                  and country_code = {} and postcode = %(in)s
                                  and geometry is not null
                    """).format(pysql.Literal(_extent_to_rank(extent)),
                                pysql.Literal(country_code)),
                pcs)


def _update_postcode_areas(conn: Connection, analyzer: AbstractAnalyzer,
                           matcher: PostcodeFormatter) -> None:
    """ Update the postcode areas made from postcode boundaries.
    """
    # first delete all areas that have gone
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
                _insert_postcode_areas(conn, country_code,
                                       matcher.get_postcode_extent(country_code), pcs)
                country_code = cc
                fmt = matcher.get_matcher(country_code)
                pcs = []
            assert fmt is not None

            if (m := fmt.match(postcode)):
                pcs.append({'out': fmt.normalize(m), 'in': postcode})

        if country_code is not None and pcs:
            _insert_postcode_areas(conn, country_code,
                                   matcher.get_postcode_extent(country_code), pcs)


def _update_guessed_postcode(conn: Connection, analyzer: AbstractAnalyzer,
                             matcher: PostcodeFormatter, project_dir: Optional[Path]) -> None:
    """ Computes artificial postcode centroids from the placex table,
        potentially enhances it with external data and then updates the
        postcodes in the table 'location_postcodes'.
    """
    # First get the list of countries that currently have postcodes.
    # (Doing this before starting to insert, so it is fast on import.)
    with conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT country_code FROM location_postcodes
                        WHERE osm_id is null""")
        todo_countries = {row[0] for row in cur}

    # Next, get the list of postcodes that are already covered by areas.
    area_pcs = defaultdict(set)
    with conn.cursor() as cur:
        cur.execute("""SELECT country_code, postcode
                       FROM location_postcodes WHERE osm_id is not null
                       ORDER BY country_code""")
        for cc, pc in cur:
            area_pcs[cc].add(pc)

    # Create a temporary table which contains coverage of the postcode areas.
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS _global_postcode_area")
        cur.execute("""CREATE TABLE _global_postcode_area AS
                       (SELECT ST_SubDivide(ST_Union(geometry)) as geometry
                        FROM place_postcode WHERE geometry is not null)
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
                    collector.commit(conn, analyzer, project_dir)
                collector = _PostcodeCollector(country, matcher.get_matcher(country),
                                               matcher.get_postcode_extent(country),
                                               exclude=area_pcs[country])
                todo_countries.discard(country)
            collector.add(postcode, x, y)

        if collector is not None:
            collector.commit(conn, analyzer, project_dir)

    # Now handle any countries that are only in the postcode table.
    for country in todo_countries:
        fmt = matcher.get_matcher(country)
        ext = matcher.get_postcode_extent(country)
        _PostcodeCollector(country, fmt, ext,
                           exclude=area_pcs[country]).commit(conn, analyzer, project_dir)

    conn.execute("DROP TABLE IF EXISTS _global_postcode_area")


def can_compute(dsn: str) -> bool:
    """ Check that the necessary tables exist so that postcodes can be computed.
    """
    with connect(dsn) as conn:
        return table_exists(conn, 'place_postcode')
