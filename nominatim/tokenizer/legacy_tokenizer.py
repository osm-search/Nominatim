"""
Tokenizer implementing normalisation as used before Nominatim 4.
"""
import logging
import shutil

import psycopg2

from nominatim.db.connection import connect
from nominatim.db import properties
from nominatim.errors import UsageError

DBCFG_NORMALIZATION = "tokenizer_normalization"

LOG = logging.getLogger()

def create(dsn, data_dir):
    """ Create a new instance of the tokenizer provided by this module.
    """
    return LegacyTokenizer(dsn, data_dir)


def _install_module(src_dir, module_dir):
    """ Copies the PostgreSQL normalisation module into the project
        directory if necessary. For historical reasons the module is
        saved in the '/module' subdirectory and not with the other tokenizer
        data.

        The function detects when the installation is run from the
        build directory. It doesn't touch the module in that case.
    """
    if module_dir.exists() and src_dir.samefile(module_dir):
        LOG.info('Running from build directory. Leaving database module as is.')
        return

    if not module_dir.exists():
        module_dir.mkdir()

    destfile = module_dir / 'nominatim.so'
    shutil.copy(str(src_dir / 'nominatim.so'), str(destfile))
    destfile.chmod(0o755)

    LOG.info('Database module installed at %s', str(destfile))


def _check_module(module_dir, conn):
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


class LegacyTokenizer:
    """ The legacy tokenizer uses a special PostgreSQL module to normalize
        names and queries. The tokenizer thus implements normalization through
        calls to the database.
    """

    def __init__(self, dsn, data_dir):
        self.dsn = dsn
        self.data_dir = data_dir
        self.normalization = None


    def init_new_db(self, config):
        """ Set up a new tokenizer for the database.

            This copies all necessary data in the project directory to make
            sure the tokenizer remains stable even over updates.
        """
        # Find and optionally install the PsotgreSQL normalization module.
        if config.DATABASE_MODULE_PATH:
            LOG.info("Using custom path for database module at '%s'",
                     config.DATABASE_MODULE_PATH)
            module_dir = config.DATABASE_MODULE_PATH
        else:
            _install_module(config.lib_dir.module, config.project_dir / 'module')
            module_dir = config.project_dir / 'module'

        self.normalization = config.TERM_NORMALIZATION

        with connect(self.dsn) as conn:
            _check_module(module_dir, conn)

            # Stable configuration is saved in the database.
            properties.set_property(conn, DBCFG_NORMALIZATION, self.normalization)

            conn.commit()


    def init_from_project(self):
        """ Initialise the tokenizer from the project directory.
        """
        with connect(self.dsn) as conn:
            self.normalization = properties.get_property(conn, DBCFG_NORMALIZATION)
