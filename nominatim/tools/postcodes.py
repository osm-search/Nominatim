"""
Functions for importing, updating and otherwise maintaining the table
of artificial postcode centroids.
"""
import csv
import gzip
import logging
from math import isfinite

from psycopg2.extras import execute_values

from nominatim.db.connection import connect

LOG = logging.getLogger()

def _to_float(num, max_value):
    """ Convert the number in string into a float. The number is expected
        to be in the range of [-max_value, max_value]. Otherwise rises a
        ValueError.
    """
    num = float(num)
    if not isfinite(num) or num <= -max_value or num >= max_value:
        raise ValueError()

    return num

class _CountryPostcodesCollector:
    """ Collector for postcodes of a single country.
    """

    def __init__(self, country):
        self.country = country
        self.collected = dict()


    def add(self, postcode, x, y):
        """ Add the given postcode to the collection cache. If the postcode
            already existed, it is overwritten with the new centroid.
        """
        self.collected[postcode] = (x, y)


    def commit(self, conn, analyzer, project_dir):
        """ Update postcodes for the country from the postcodes selected so far
            as well as any externally supplied postcodes.
        """
        self._update_from_external(analyzer, project_dir)
        to_add, to_delete, to_update = self._compute_changes(conn)

        LOG.info("Processing country '%s' (%s added, %s deleted, %s updated).",
                 self.country, len(to_add), len(to_delete), len(to_update))

        with conn.cursor() as cur:
            if to_add:
                execute_values(cur,
                               """INSERT INTO location_postcode
                                      (place_id, indexed_status, country_code,
                                       postcode, geometry) VALUES %s""",
                               to_add,
                               template="""(nextval('seq_place'), 1, '{}',
                                           %s, 'SRID=4326;POINT(%s %s)')
                                        """.format(self.country))
            if to_delete:
                cur.execute("""DELETE FROM location_postcode
                               WHERE country_code = %s and postcode = any(%s)
                            """, (self.country, to_delete))
            if to_update:
                execute_values(cur,
                               """UPDATE location_postcode
                                  SET indexed_status = 2,
                                      geometry = ST_SetSRID(ST_Point(v.x, v.y), 4326)
                                  FROM (VALUES %s) AS v (pc, x, y)
                                  WHERE country_code = '{}' and postcode = pc
                               """.format(self.country),
                               to_update)


    def _compute_changes(self, conn):
        """ Compute which postcodes from the collected postcodes have to be
            added or modified and which from the location_postcode table
            have to be deleted.
        """
        to_update = []
        to_delete = []
        with conn.cursor() as cur:
            cur.execute("""SELECT postcode, ST_X(geometry), ST_Y(geometry)
                           FROM location_postcode
                           WHERE country_code = %s""",
                        (self.country, ))
            for postcode, x, y in cur:
                newx, newy = self.collected.pop(postcode, (None, None))
                if newx is not None:
                    dist = (x - newx)**2 + (y - newy)**2
                    if dist > 0.0000001:
                        to_update.append((postcode, newx, newy))
                else:
                    to_delete.append(postcode)

        to_add = [(k, v[0], v[1]) for k, v in self.collected.items()]
        self.collected = []

        return to_add, to_delete, to_update


    def _update_from_external(self, analyzer, project_dir):
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
                        self.collected[postcode] = (_to_float(row['lon'], 180),
                                                    _to_float(row['lat'], 90))
                    except ValueError:
                        LOG.warning("Bad coordinates %s, %s in %s country postcode file.",
                                    row['lat'], row['lon'], self.country)

        finally:
            csvfile.close()


    def _open_external(self, project_dir):
        fname = project_dir / '{}_postcodes.csv'.format(self.country)

        if fname.is_file():
            LOG.info("Using external postcode file '%s'.", fname)
            return open(fname, 'r')

        fname = project_dir / '{}_postcodes.csv.gz'.format(self.country)

        if fname.is_file():
            LOG.info("Using external postcode file '%s'.", fname)
            return gzip.open(fname, 'rt')

        return None


def update_postcodes(dsn, project_dir, tokenizer):
    """ Update the table of artificial postcodes.

        Computes artificial postcode centroids from the placex table,
        potentially enhances it with external data and then updates the
        postcodes in the table 'location_postcode'.
    """
    with tokenizer.name_analyzer() as analyzer:
        with connect(dsn) as conn:
            # First get the list of countries that currently have postcodes.
            # (Doing this before starting to insert, so it is fast on import.)
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT country_code FROM location_postcode")
                todo_countries = set((row[0] for row in cur))

            # Recompute the list of valid postcodes from placex.
            with conn.cursor(name="placex_postcodes") as cur:
                cur.execute("""
                SELECT cc as country_code, pc, ST_X(centroid), ST_Y(centroid)
                FROM (
                    SELECT 
                        COALESCE(plx.country_code, get_country_code(ST_Centroid(pl.geometry))) as cc,
                        token_normalized_postcode(pl.address->'postcode') as pc,
                        COALESCE(ST_Centroid(ST_Collect(plx.centroid)), ST_Centroid(ST_Collect(ST_Centroid(pl.geometry)))) as centroid
                    FROM place AS pl LEFT OUTER JOIN placex AS plx ON pl.osm_id = plx.osm_id AND pl.osm_type = plx.osm_type
                    WHERE pl.address ? 'postcode' AND pl.geometry IS NOT null
                    GROUP BY cc, pc
                ) xx
                WHERE pc IS NOT null AND cc IS NOT null
                ORDER BY country_code, pc""")

                collector = None

                for country, postcode, x, y in cur:
                    if collector is None or country != collector.country:
                        if collector is not None:
                            collector.commit(conn, analyzer, project_dir)
                        collector = _CountryPostcodesCollector(country)
                        todo_countries.discard(country)
                    collector.add(postcode, x, y)

                if collector is not None:
                    collector.commit(conn, analyzer, project_dir)

            # Now handle any countries that are only in the postcode table.
            for country in todo_countries:
                _CountryPostcodesCollector(country).commit(conn, analyzer, project_dir)

            conn.commit()

        analyzer.update_postcodes_from_db()

def can_compute(dsn):
    """
        Check that the place table exists so that
        postcodes can be computed.
    """
    with connect(dsn) as conn:
        return conn.table_exists('place')
