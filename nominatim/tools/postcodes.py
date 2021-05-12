"""
Functions for importing, updating and otherwise maintaining the table
of artificial postcode centroids.
"""
import csv
import gzip
import logging

from psycopg2.extras import execute_values

from nominatim.db.connection import connect

LOG = logging.getLogger()

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

        with conn.cursor() as cur:
            if to_add:
                execute_values(cur,
                               """INSERT INTO location_postcodes
                                      (place_id, indexed_status, countrycode,
                                       postcode, geometry) VALUES %s""",
                               to_add,
                               template="""(nextval('seq_place'), 1, '{}',
                                           %s, 'SRID=4326;POINT(%s %s)')
                                        """.format(self.country))
            if to_delete:
                cur.execute("""DELETE FROM location_postcodes
                               WHERE country_code = %s and postcode = any(%s)
                            """, (self.country, to_delete))
            if to_update:
                execute_values(cur,
                               """UPDATE location_postcodes
                                  SET indexed_status = 2,
                                      geometry = ST_SetSRID(ST_Point(v.x, v.y), 4326)
                                  FROM (VALUES %s) AS v (pc, x, y)
                                  WHERE country_code = '{}' and postcode = pc
                               """.format(self.country),
                               to_update)


    def _compute_changes(self, conn):
        """ Compute which postcodes from the collected postcodes have to be
            added or modified and which from the location_postcodes table
            have to be deleted.
        """
        to_update = []
        to_delete = []
        with conn.cursor() as cur:
            cur.execute("""SELECT postcode, ST_X(geometry), ST_Y(geometry)
                           FROM location_postcodes
                           WHERE country_code = %s""",
                        (self.country, ))
            for postcode, x, y in cur:
                oldx, oldy = self.collected.pop(postcode, (None, None))
                if oldx is not None:
                    dist = (x - oldx)**2 + (y - oldy)**2
                    if dist > 0.000001:
                        to_update.append(postcode, x, y)
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
                        self.collected[postcode] = (float(row['lon'], float(row['lat'])))
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
            with conn.cursor("placex_postcodes") as cur:
                cur.execute("""SELECT country_code, pc, ST_X(centroid), ST_Y(centroid)
                               FROM (
                                 SELECT country_code,
                                        token_normalized_postcode(address->'postcode') as pc,
                                        ST_Centroid(ST_Collect(ST_Centroid(geometry))) as centroid
                                 FROM placex
                                 WHERE address ? 'postcode' and geometry IS NOT null
                                 GROUP BY country_code, pc) xx
                               WHERE pc is not null
                               ORDER BY country_code, pc""")

                collector = None

                for country, postcode, x, y in cur:
                    if collector is None or country != collector.country:
                        if collector is not None:
                            collector.commit(conn, analyzer, project_dir)
                        collector = _CountryPostcodesCollector(country)
                    collector.add(postcode, x, y)

                if collector is not None:
                    collector.commit(conn, analyzer, project_dir)

            conn.commit()

        analyzer.add_postcodes_from_db()
