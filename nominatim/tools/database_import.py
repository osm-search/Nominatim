# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for setting up and importing a new Nominatim database.
"""
from typing import Tuple, Optional, Union, Sequence, MutableMapping, Any
import logging
import os
import selectors
import subprocess
from pathlib import Path

import psutil
from psycopg2 import sql as pysql

from nominatim.config import Configuration
from nominatim.db.connection import connect, get_pg_env, Connection
from nominatim.db.async_connection import DBConnection
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.tools.exec_utils import run_osm2pgsql
from nominatim.errors import UsageError
from nominatim.version import POSTGRESQL_REQUIRED_VERSION, POSTGIS_REQUIRED_VERSION

LOG = logging.getLogger()

def _require_version(module: str, actual: Tuple[int, int], expected: Tuple[int, int]) -> None:
    """ Compares the version for the given module and raises an exception
        if the actual version is too old.
    """
    if actual < expected:
        LOG.fatal('Minimum supported version of %s is %d.%d. '
                  'Found version %d.%d.',
                  module, expected[0], expected[1], actual[0], actual[1])
        raise UsageError(f'{module} is too old.')


def setup_database_skeleton(dsn: str, rouser: Optional[str] = None) -> None:
    """ Create a new database for Nominatim and populate it with the
        essential extensions.

        The function fails when the database already exists or Postgresql or
        PostGIS versions are too old.

        Uses `createdb` to create the database.

        If 'rouser' is given, then the function also checks that the user
        with that given name exists.

        Requires superuser rights by the caller.
    """
    proc = subprocess.run(['createdb'], env=get_pg_env(dsn), check=False)

    if proc.returncode != 0:
        raise UsageError('Creating new database failed.')

    with connect(dsn) as conn:
        _require_version('PostgreSQL server',
                         conn.server_version_tuple(),
                         POSTGRESQL_REQUIRED_VERSION)

        if rouser is not None:
            with conn.cursor() as cur:
                cnt = cur.scalar('SELECT count(*) FROM pg_user where usename = %s',
                                 (rouser, ))
                if cnt == 0:
                    LOG.fatal("Web user '%s' does not exist. Create it with:\n"
                              "\n      createuser %s", rouser, rouser)
                    raise UsageError('Missing read-only user.')

        # Create extensions.
        with conn.cursor() as cur:
            cur.execute('CREATE EXTENSION IF NOT EXISTS hstore')
            cur.execute('CREATE EXTENSION IF NOT EXISTS postgis')
            cur.execute('CREATE EXTENSION IF NOT EXISTS postgis_raster')
        conn.commit()

        _require_version('PostGIS',
                         conn.postgis_version_tuple(),
                         POSTGIS_REQUIRED_VERSION)


def import_osm_data(osm_files: Union[Path, Sequence[Path]],
                    options: MutableMapping[str, Any],
                    drop: bool = False, ignore_errors: bool = False) -> None:
    """ Import the given OSM files. 'options' contains the list of
        default settings for osm2pgsql.
    """
    options['import_file'] = osm_files
    options['append'] = False
    options['threads'] = 1

    if not options['flatnode_file'] and options['osm2pgsql_cache'] == 0:
        # Make some educated guesses about cache size based on the size
        # of the import file and the available memory.
        mem = psutil.virtual_memory()
        fsize = 0
        if isinstance(osm_files, list):
            for fname in osm_files:
                fsize += os.stat(str(fname)).st_size
        else:
            fsize = os.stat(str(osm_files)).st_size
        options['osm2pgsql_cache'] = int(min((mem.available + mem.cached) * 0.75,
                                             fsize * 2) / 1024 / 1024) + 1

    run_osm2pgsql(options)

    with connect(options['dsn']) as conn:
        if not ignore_errors:
            with conn.cursor() as cur:
                cur.execute('SELECT * FROM place LIMIT 1')
                if cur.rowcount == 0:
                    raise UsageError('No data imported by osm2pgsql.')

        if drop:
            conn.drop_table('planet_osm_nodes')

    if drop and options['flatnode_file']:
        Path(options['flatnode_file']).unlink()


def create_tables(conn: Connection, config: Configuration, reverse_only: bool = False) -> None:
    """ Create the set of basic tables.
        When `reverse_only` is True, then the main table for searching will
        be skipped and only reverse search is possible.
    """
    sql = SQLPreprocessor(conn, config)
    sql.env.globals['db']['reverse_only'] = reverse_only

    sql.run_sql_file(conn, 'tables.sql')


def create_table_triggers(conn: Connection, config: Configuration) -> None:
    """ Create the triggers for the tables. The trigger functions must already
        have been imported with refresh.create_functions().
    """
    sql = SQLPreprocessor(conn, config)
    sql.run_sql_file(conn, 'table-triggers.sql')


def create_partition_tables(conn: Connection, config: Configuration) -> None:
    """ Create tables that have explicit partitioning.
    """
    sql = SQLPreprocessor(conn, config)
    sql.run_sql_file(conn, 'partition-tables.src.sql')


def truncate_data_tables(conn: Connection) -> None:
    """ Truncate all data tables to prepare for a fresh load.
    """
    with conn.cursor() as cur:
        cur.execute('TRUNCATE placex')
        cur.execute('TRUNCATE place_addressline')
        cur.execute('TRUNCATE location_area')
        cur.execute('TRUNCATE location_area_country')
        cur.execute('TRUNCATE location_property_tiger')
        cur.execute('TRUNCATE location_property_osmline')
        cur.execute('TRUNCATE location_postcode')
        if conn.table_exists('search_name'):
            cur.execute('TRUNCATE search_name')
        cur.execute('DROP SEQUENCE IF EXISTS seq_place')
        cur.execute('CREATE SEQUENCE seq_place start 100000')

        cur.execute("""SELECT tablename FROM pg_tables
                       WHERE tablename LIKE 'location_road_%'""")

        for table in [r[0] for r in list(cur)]:
            cur.execute('TRUNCATE ' + table)

    conn.commit()


_COPY_COLUMNS = pysql.SQL(',').join(map(pysql.Identifier,
                                        ('osm_type', 'osm_id', 'class', 'type',
                                         'name', 'admin_level', 'address',
                                         'extratags', 'geometry')))


def load_data(dsn: str, threads: int) -> None:
    """ Copy data into the word and placex table.
    """
    sel = selectors.DefaultSelector()
    # Then copy data from place to placex in <threads - 1> chunks.
    place_threads = max(1, threads - 1)
    for imod in range(place_threads):
        conn = DBConnection(dsn)
        conn.connect()
        conn.perform(
            pysql.SQL("""INSERT INTO placex ({columns})
                           SELECT {columns} FROM place
                           WHERE osm_id % {total} = {mod}
                             AND NOT (class='place' and (type='houses' or type='postcode'))
                             AND ST_IsValid(geometry)
                      """).format(columns=_COPY_COLUMNS,
                                  total=pysql.Literal(place_threads),
                                  mod=pysql.Literal(imod)))
        sel.register(conn, selectors.EVENT_READ, conn)

    # Address interpolations go into another table.
    conn = DBConnection(dsn)
    conn.connect()
    conn.perform("""INSERT INTO location_property_osmline (osm_id, address, linegeo)
                      SELECT osm_id, address, geometry FROM place
                      WHERE class='place' and type='houses' and osm_type='W'
                            and ST_GeometryType(geometry) = 'ST_LineString'
                 """)
    sel.register(conn, selectors.EVENT_READ, conn)

    # Now wait for all of them to finish.
    todo = place_threads + 1
    while todo > 0:
        for key, _ in sel.select(1):
            conn = key.data
            sel.unregister(conn)
            conn.wait()
            conn.close()
            todo -= 1
        print('.', end='', flush=True)
    print('\n')

    with connect(dsn) as syn_conn:
        with syn_conn.cursor() as cur:
            cur.execute('ANALYSE')


def create_search_indices(conn: Connection, config: Configuration,
                          drop: bool = False, threads: int = 1) -> None:
    """ Create tables that have explicit partitioning.
    """

    # If index creation failed and left an index invalid, they need to be
    # cleaned out first, so that the script recreates them.
    with conn.cursor() as cur:
        cur.execute("""SELECT relname FROM pg_class, pg_index
                       WHERE pg_index.indisvalid = false
                             AND pg_index.indexrelid = pg_class.oid""")
        bad_indices = [row[0] for row in list(cur)]
        for idx in bad_indices:
            LOG.info("Drop invalid index %s.", idx)
            cur.execute(pysql.SQL('DROP INDEX {}').format(pysql.Identifier(idx)))
    conn.commit()

    sql = SQLPreprocessor(conn, config)

    sql.run_parallel_sql_file(config.get_libpq_dsn(),
                              'indices.sql', min(8, threads), drop=drop)


def import_osm_views_geotiff():
    """Import OSM views GeoTIFF file"""
    subprocess.run("raster2pgsql -s 4326 -I -C -t 100x100 -e osmviews.tiff public.osmviews | psql nominatim", shell=True, check=True)
