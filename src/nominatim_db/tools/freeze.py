# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for removing unnecessary data from the database.
"""
from typing import Optional
from pathlib import Path

from psycopg import sql as pysql

from ..db.connection import Connection, drop_tables, table_exists

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


def drop_update_tables(conn: Connection) -> None:
    """ Drop all tables only necessary for updating the database from
        OSM replication data.
    """
    parts = (pysql.SQL("(tablename LIKE {})").format(pysql.Literal(t)) for t in UPDATE_TABLES)

    with conn.cursor() as cur:
        cur.execute(pysql.SQL("SELECT tablename FROM pg_tables WHERE ")
                    + pysql.SQL(' or ').join(parts))
        tables = [r[0] for r in cur]

    drop_tables(conn, *tables, cascade=True)
    conn.commit()


def drop_flatnode_file(fpath: Optional[Path]) -> None:
    """ Remove the flatnode file if it exists.
    """
    if fpath and fpath.exists():
        fpath.unlink()


def is_frozen(conn: Connection) -> bool:
    """ Returns true if database is in a frozen state
    """
    return table_exists(conn, 'place') is False
