"""
Functions for removing unnecessary data from the database.
"""
from pathlib import Path

UPDATE_TABLES = [
    'address_levels',
    'gb_postcode',
    'import_osmosis_log',
    'import_polygon_%',
    'location_area%',
    'location_road%',
    'place',
    'planet_osm_%',
    'search_name_%',
    'us_postcode',
    'wikipedia_%'
]

def drop_update_tables(conn):
    """ Drop all tables only necessary for updating the database from
        OSM replication data.
    """

    where = ' or '.join(["(tablename LIKE '{}')".format(t) for t in UPDATE_TABLES])

    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE " + where)
        tables = [r[0] for r in cur]

        for table in tables:
            cur.drop_table(table, cascade=True)

    conn.commit()


def drop_flatnode_file(fname):
    """ Remove the flatnode file if it exists.
    """
    if fname:
        fpath = Path(fname)
        if fpath.exists():
            fpath.unlink()
