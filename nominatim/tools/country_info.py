"""
Functions for importing and managing static country information.
"""
from nominatim.db import utils as db_utils
from nominatim.db.connection import connect

def setup_country_tables(dsn, sql_dir, ignore_partitions=False):
    """ Create and populate the tables with basic static data that provides
        the background for geocoding. Data is assumed to not yet exist.
    """
    db_utils.execute_file(dsn, sql_dir / 'country_name.sql')
    db_utils.execute_file(dsn, sql_dir / 'country_osm_grid.sql.gz')

    if ignore_partitions:
        with connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE country_name SET partition = 0')
            conn.commit()
