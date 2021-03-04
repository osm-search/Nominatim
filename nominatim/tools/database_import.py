"""
Functions for setting up and importing a new Nominatim database.
"""
import logging
import os
import selectors
import subprocess
import shutil
from pathlib import Path

import psutil
import psycopg2

from ..db.connection import connect, get_pg_env
from ..db import utils as db_utils
from ..db.async_connection import DBConnection
from ..db.sql_preprocessor import SQLPreprocessor
from .exec_utils import run_osm2pgsql
from ..errors import UsageError
from ..version import POSTGRESQL_REQUIRED_VERSION, POSTGIS_REQUIRED_VERSION

LOG = logging.getLogger()

def setup_database_skeleton(dsn, data_dir, no_partitions, rouser=None):
    """ Create a new database for Nominatim and populate it with the
        essential extensions and data.
    """
    LOG.warning('Creating database')
    create_db(dsn, rouser)

    LOG.warning('Setting up database')
    with connect(dsn) as conn:
        setup_extensions(conn)

    LOG.warning('Loading basic data')
    import_base_data(dsn, data_dir, no_partitions)


def create_db(dsn, rouser=None):
    """ Create a new database for the given DSN. Fails when the database
        already exists or the PostgreSQL version is too old.
        Uses `createdb` to create the database.

        If 'rouser' is given, then the function also checks that the user
        with that given name exists.

        Requires superuser rights by the caller.
    """
    proc = subprocess.run(['createdb'], env=get_pg_env(dsn), check=False)

    if proc.returncode != 0:
        raise UsageError('Creating new database failed.')

    with connect(dsn) as conn:
        postgres_version = conn.server_version_tuple()
        if postgres_version < POSTGRESQL_REQUIRED_VERSION:
            LOG.fatal('Minimum supported version of Postgresql is %d.%d. '
                      'Found version %d.%d.',
                      POSTGRESQL_REQUIRED_VERSION[0], POSTGRESQL_REQUIRED_VERSION[1],
                      postgres_version[0], postgres_version[1])
            raise UsageError('PostgreSQL server is too old.')

        if rouser is not None:
            with conn.cursor() as cur:
                cnt = cur.scalar('SELECT count(*) FROM pg_user where usename = %s',
                                 (rouser, ))
                if cnt == 0:
                    LOG.fatal("Web user '%s' does not exists. Create it with:\n"
                              "\n      createuser %s", rouser, rouser)
                    raise UsageError('Missing read-only user.')



def setup_extensions(conn):
    """ Set up all extensions needed for Nominatim. Also checks that the
        versions of the extensions are sufficient.
    """
    with conn.cursor() as cur:
        cur.execute('CREATE EXTENSION IF NOT EXISTS hstore')
        cur.execute('CREATE EXTENSION IF NOT EXISTS postgis')
    conn.commit()

    postgis_version = conn.postgis_version_tuple()
    if postgis_version < POSTGIS_REQUIRED_VERSION:
        LOG.fatal('Minimum supported version of PostGIS is %d.%d. '
                  'Found version %d.%d.',
                  POSTGIS_REQUIRED_VERSION[0], POSTGIS_REQUIRED_VERSION[1],
                  postgis_version[0], postgis_version[1])
        raise UsageError('PostGIS version is too old.')


def install_module(src_dir, project_dir, module_dir, conn=None):
    """ Copy the normalization module from src_dir into the project
        directory under the '/module' directory. If 'module_dir' is set, then
        use the module from there instead and check that it is accessible
        for Postgresql.

        The function detects when the installation is run from the
        build directory. It doesn't touch the module in that case.

        If 'conn' is given, then the function also tests if the module
        can be access via the given database.
    """
    if not module_dir:
        module_dir = project_dir / 'module'

        if not module_dir.exists() or not src_dir.samefile(module_dir):

            if not module_dir.exists():
                module_dir.mkdir()

            destfile = module_dir / 'nominatim.so'
            shutil.copy(str(src_dir / 'nominatim.so'), str(destfile))
            destfile.chmod(0o755)

            LOG.info('Database module installed at %s', str(destfile))
        else:
            LOG.info('Running from build directory. Leaving database module as is.')
    else:
        LOG.info("Using custom path for database module at '%s'", module_dir)

    if conn is not None:
        with conn.cursor() as cur:
            try:
                cur.execute("""CREATE FUNCTION nominatim_test_import_func(text)
                               RETURNS text AS '{}/nominatim.so', 'transliteration'
                               LANGUAGE c IMMUTABLE STRICT;
                               DROP FUNCTION nominatim_test_import_func(text)
                            """.format(module_dir))
            except psycopg2.DatabaseError as err:
                LOG.fatal("Error accessing database module: %s", err)
                raise UsageError("Database module cannot be accessed.") from err


def import_base_data(dsn, sql_dir, ignore_partitions=False):
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


def import_osm_data(osm_file, options, drop=False, ignore_errors=False):
    """ Import the given OSM file. 'options' contains the list of
        default settings for osm2pgsql.
    """
    options['import_file'] = osm_file
    options['append'] = False
    options['threads'] = 1

    if not options['flatnode_file'] and options['osm2pgsql_cache'] == 0:
        # Make some educated guesses about cache size based on the size
        # of the import file and the available memory.
        mem = psutil.virtual_memory()
        fsize = os.stat(str(osm_file)).st_size
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

    if drop:
        if options['flatnode_file']:
            Path(options['flatnode_file']).unlink()


def create_tables(conn, config, sqllib_dir, reverse_only=False):
    """ Create the set of basic tables.
        When `reverse_only` is True, then the main table for searching will
        be skipped and only reverse search is possible.
    """
    sql = SQLPreprocessor(conn, config, sqllib_dir)
    sql.env.globals['db']['reverse_only'] = reverse_only

    sql.run_sql_file(conn, 'tables.sql')


def create_table_triggers(conn, config, sqllib_dir):
    """ Create the triggers for the tables. The trigger functions must already
        have been imported with refresh.create_functions().
    """
    sql = SQLPreprocessor(conn, config, sqllib_dir)
    sql.run_sql_file(conn, 'table-triggers.sql')


def create_partition_tables(conn, config, sqllib_dir):
    """ Create tables that have explicit partitioning.
    """
    sql = SQLPreprocessor(conn, config, sqllib_dir)
    sql.run_sql_file(conn, 'partition-tables.src.sql')


def truncate_data_tables(conn, max_word_frequency=None):
    """ Truncate all data tables to prepare for a fresh load.
    """
    with conn.cursor() as cur:
        cur.execute('TRUNCATE word')
        cur.execute('TRUNCATE placex')
        cur.execute('TRUNCATE place_addressline')
        cur.execute('TRUNCATE location_area')
        cur.execute('TRUNCATE location_area_country')
        cur.execute('TRUNCATE location_property')
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

        if max_word_frequency is not None:
            # Used by getorcreate_word_id to ignore frequent partial words.
            cur.execute("""CREATE OR REPLACE FUNCTION get_maxwordfreq()
                           RETURNS integer AS $$
                             SELECT {} as maxwordfreq;
                           $$ LANGUAGE SQL IMMUTABLE
                        """.format(max_word_frequency))
        conn.commit()

_COPY_COLUMNS = 'osm_type, osm_id, class, type, name, admin_level, address, extratags, geometry'

def load_data(dsn, data_dir, threads):
    """ Copy data into the word and placex table.
    """
    # Pre-calculate the most important terms in the word list.
    db_utils.execute_file(dsn, data_dir / 'words.sql')

    sel = selectors.DefaultSelector()
    # Then copy data from place to placex in <threads - 1> chunks.
    place_threads = max(1, threads - 1)
    for imod in range(place_threads):
        conn = DBConnection(dsn)
        conn.connect()
        conn.perform("""INSERT INTO placex ({0})
                         SELECT {0} FROM place
                         WHERE osm_id % {1} = {2}
                           AND NOT (class='place' and type='houses')
                           AND ST_IsValid(geometry)
                     """.format(_COPY_COLUMNS, place_threads, imod))
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

    with connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute('ANALYSE')


def create_search_indices(conn, config, sqllib_dir, drop=False):
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
            cur.execute('DROP INDEX "{}"'.format(idx))
    conn.commit()

    sql = SQLPreprocessor(conn, config, sqllib_dir)

    sql.run_sql_file(conn, 'indices.sql', drop=drop)
