"""
Tokenizer implementing normalisation as used before Nominatim 4.
"""
import logging
import shutil

import psycopg2
import psycopg2.extras

from nominatim.db.connection import connect
from nominatim.db import properties
from nominatim.db import utils as db_utils
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.errors import UsageError

DBCFG_NORMALIZATION = "tokenizer_normalization"
DBCFG_MAXWORDFREQ = "tokenizer_maxwordfreq"

LOG = logging.getLogger()

def create(dsn, data_dir):
    """ Create a new instance of the tokenizer provided by this module.
    """
    return LegacyTokenizer(dsn, data_dir)


def _install_module(config_module_path, src_dir, module_dir):
    """ Copies the PostgreSQL normalisation module into the project
        directory if necessary. For historical reasons the module is
        saved in the '/module' subdirectory and not with the other tokenizer
        data.

        The function detects when the installation is run from the
        build directory. It doesn't touch the module in that case.
    """
    # Custom module locations are simply used as is.
    if config_module_path:
        LOG.info("Using custom path for database module at '%s'", config_module_path)
        return config_module_path

    # Compatibility mode for builddir installations.
    if module_dir.exists() and src_dir.samefile(module_dir):
        LOG.info('Running from build directory. Leaving database module as is.')
        return module_dir

    # In any other case install the module in the project directory.
    if not module_dir.exists():
        module_dir.mkdir()

    destfile = module_dir / 'nominatim.so'
    shutil.copy(str(src_dir / 'nominatim.so'), str(destfile))
    destfile.chmod(0o755)

    LOG.info('Database module installed at %s', str(destfile))

    return module_dir


def _check_module(module_dir, conn):
    """ Try to use the PostgreSQL module to confirm that it is correctly
        installed and accessible from PostgreSQL.
    """
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
        module_dir = _install_module(config.DATABASE_MODULE_PATH,
                                     config.lib_dir.module,
                                     config.project_dir / 'module')

        self.normalization = config.TERM_NORMALIZATION

        with connect(self.dsn) as conn:
            _check_module(module_dir, conn)
            self._save_config(conn, config)
            conn.commit()

        self.update_sql_functions(config)
        self._init_db_tables(config)


    def init_from_project(self):
        """ Initialise the tokenizer from the project directory.
        """
        with connect(self.dsn) as conn:
            self.normalization = properties.get_property(conn, DBCFG_NORMALIZATION)


    def update_sql_functions(self, config):
        """ Reimport the SQL functions for this tokenizer.
        """
        with connect(self.dsn) as conn:
            max_word_freq = properties.get_property(conn, DBCFG_MAXWORDFREQ)
            modulepath = config.DATABASE_MODULE_PATH or \
                         str((config.project_dir / 'module').resolve())
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_tokenizer.sql',
                              max_word_freq=max_word_freq,
                              modulepath=modulepath)


    def migrate_database(self, config):
        """ Initialise the project directory of an existing database for
            use with this tokenizer.

            This is a special migration function for updating existing databases
            to new software versions.
        """
        module_dir = _install_module(config.DATABASE_MODULE_PATH,
                                     config.lib_dir.module,
                                     config.project_dir / 'module')

        with connect(self.dsn) as conn:
            _check_module(module_dir, conn)
            self._save_config(conn, config)


    def name_analyzer(self):
        """ Create a new analyzer for tokenizing names and queries
            using this tokinzer. Analyzers are context managers and should
            be used accordingly:

            ```
            with tokenizer.name_analyzer() as analyzer:
                analyser.tokenize()
            ```

            When used outside the with construct, the caller must ensure to
            call the close() function before destructing the analyzer.

            Analyzers are not thread-safe. You need to instantiate one per thread.
        """
        return LegacyNameAnalyzer(self.dsn)


    def _init_db_tables(self, config):
        """ Set up the word table and fill it with pre-computed word
            frequencies.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_tokenizer_tables.sql')
            conn.commit()

        LOG.warning("Precomputing word tokens")
        db_utils.execute_file(self.dsn, config.lib_dir.data / 'words.sql')


    def _save_config(self, conn, config):
        """ Save the configuration that needs to remain stable for the given
            database as database properties.
        """
        properties.set_property(conn, DBCFG_NORMALIZATION, self.normalization)
        properties.set_property(conn, DBCFG_MAXWORDFREQ, config.MAX_WORD_FREQUENCY)



class LegacyNameAnalyzer:
    """ The legacy analyzer uses the special Postgresql module for
        splitting names.

        Each instance opens a connection to the database to request the
        normalization.
    """

    def __init__(self, dsn):
        self.conn = connect(dsn).connection
        self.conn.autocommit = True
        psycopg2.extras.register_hstore(self.conn)


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def close(self):
        """ Free all resources used by the analyzer.
        """
        if self.conn:
            self.conn.close()
            self.conn = None

    def process_place(self, place):
        """ Determine tokenizer information about the given place.

            Returns a JSON-serialisable structure that will be handed into
            the database via the token_info field.
        """
        return {}
