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

from ..db.connection import Connection, drop_tables, table_exists, connect
from ..config import Configuration

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


def _install_frozen_partition_functions(conn: Connection, config: Configuration) -> None:
    """Frozen versions of partition-functions.sql"""

    frozen_functions_file = config.lib_dir.sql / 'functions' / 'frozen-db-functions.sql'

    if not frozen_functions_file.exists():
        raise FileNotFoundError(
            f"Frozen SQL functions file not found at: {frozen_functions_file}"
        )

    with open(frozen_functions_file, 'r') as f:
        sql_code = f.read()

    try:
        with conn.cursor() as cur:
            # TODO: execute needs LiteralString
            cur.execute(sql_code)  # tyoe: ignore [arg-type]
        conn.commit()

    except Exception as e:
        conn.rollback()
        raise RuntimeError(f"Failed to install frozen-db-functions.sql: {e}") from e


def freeze(config: Configuration) -> None:
    """Freeze the database for read-only operation."""
    try:
        with connect(config.get_libpq_dsn()) as connection:
            drop_update_tables(connection)
            _install_frozen_partition_functions(connection, config)
        drop_flatnode_file(config.get_path('FLATNODE_FILE'))

    except Exception as e:
        print(f"FREEZE ERROR: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        raise


def drop_flatnode_file(fpath: Optional[Path]) -> None:
    """ Remove the flatnode file if it exists.
    """
    if fpath and fpath.exists():
        fpath.unlink()


def is_frozen(conn: Connection) -> bool:
    """ Returns true if database is in a frozen state
    """
    return table_exists(conn, 'place') is False
