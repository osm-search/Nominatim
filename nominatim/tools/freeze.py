# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for removing unnecessary data from the database.
"""
from pathlib import Path

from psycopg2 import sql as pysql

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
    parts = (pysql.SQL("(tablename LIKE {})").format(pysql.Literal(t)) for t in UPDATE_TABLES)

    with conn.cursor() as cur:
        cur.execute(pysql.SQL("SELECT tablename FROM pg_tables WHERE ")
                    + pysql.SQL(' or ').join(parts))
        tables = [r[0] for r in cur]

        for table in tables:
            cur.drop_table(table, cascade=True)

    conn.commit()


def drop_flatnode_file(fpath):
    """ Remove the flatnode file if it exists.
    """
    if fpath and fpath.exists():
        fpath.unlink()
