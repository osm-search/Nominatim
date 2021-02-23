"""
Functions for setting up and importing a new Nominatim database.
"""
import logging
import subprocess
import shutil

from ..db.connection import connect, get_pg_env
from ..db import utils as db_utils
from ..errors import UsageError
from ..version import POSTGRESQL_REQUIRED_VERSION, POSTGIS_REQUIRED_VERSION

LOG = logging.getLogger()

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
        postgres_version = conn.server_version_tuple() # pylint: disable=E1101
        if postgres_version < POSTGRESQL_REQUIRED_VERSION:
            LOG.fatal('Minimum supported version of Postgresql is %d.%d. '
                      'Found version %d.%d.',
                      POSTGRESQL_REQUIRED_VERSION[0], POSTGRESQL_REQUIRED_VERSION[1],
                      postgres_version[0], postgres_version[1])
            raise UsageError('PostgreSQL server is too old.')

        if rouser is not None:
            with conn.cursor() as cur:  # pylint: disable=E1101
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


def install_module(src_dir, project_dir, module_dir):
    """ Copy the normalization module from src_dir into the project
        directory under the '/module' directory. If 'module_dir' is set, then
        use the module from there instead and check that it is accessible
        for Postgresql.

        The function detects when the installation is run from the
        build directory. It doesn't touch the module in that case.
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

    return module_dir


def check_module_dir_path(conn, path):
    """ Check that the normalisation module can be found and executed
        from the given path.
    """
    with conn.cursor() as cur:
        cur.execute("""CREATE FUNCTION nominatim_test_import_func(text)
                       RETURNS text AS '{}/nominatim.so', 'transliteration'
                       LANGUAGE c IMMUTABLE STRICT;
                       DROP FUNCTION nominatim_test_import_func(text)
                    """.format(path))


def import_base_data(dsn, sql_dir, ignore_partitions=False):
    """ Create and populate the tables with basic static data that provides
        the background for geocoding.
    """
    db_utils.execute_file(dsn, sql_dir / 'country_name.sql')
    db_utils.execute_file(dsn, sql_dir / 'country_osm_grid.sql.gz')

    if ignore_partitions:
        with connect(dsn) as conn:
            with conn.cursor() as cur:  # pylint: disable=E1101
                cur.execute('UPDATE country_name SET partition = 0')
            conn.commit()  # pylint: disable=E1101
