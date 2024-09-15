# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
from pathlib import Path
import importlib
import tempfile

import psycopg
from psycopg import sql as pysql

from nominatim_db import cli
from nominatim_db.config import Configuration
from nominatim_db.db.connection import Connection, register_hstore, execute_scalar
from nominatim_db.tools import refresh
from nominatim_db.tokenizer import factory as tokenizer_factory
from steps.utils import run_script

class NominatimEnvironment:
    """ Collects all functions for the execution of Nominatim functions.
    """

    def __init__(self, config):
        self.src_dir = (Path(__file__) / '..' / '..' / '..' / '..').resolve()
        self.db_host = config['DB_HOST']
        self.db_port = config['DB_PORT']
        self.db_user = config['DB_USER']
        self.db_pass = config['DB_PASS']
        self.template_db = config['TEMPLATE_DB']
        self.test_db = config['TEST_DB']
        self.api_test_db = config['API_TEST_DB']
        self.api_test_file = config['API_TEST_FILE']
        self.tokenizer = config['TOKENIZER']
        self.import_style = config['STYLE']
        self.server_module_path = config['SERVER_MODULE_PATH']
        self.reuse_template = not config['REMOVE_TEMPLATE']
        self.keep_scenario_db = config['KEEP_TEST_DB']

        self.default_config = Configuration(None).get_os_env()
        self.test_env = None
        self.template_db_done = False
        self.api_db_done = False
        self.website_dir = None

        if not hasattr(self, f"create_api_request_func_{config['API_ENGINE']}"):
            raise RuntimeError(f"Unknown API engine '{config['API_ENGINE']}'")
        self.api_engine = getattr(self, f"create_api_request_func_{config['API_ENGINE']}")()

        if self.tokenizer == 'legacy' and self.server_module_path is None:
            raise RuntimeError("You must set -DSERVER_MODULE_PATH when testing the legacy tokenizer.")

    def connect_database(self, dbname):
        """ Return a connection to the database with the given name.
            Uses configured host, user and port.
        """
        dbargs = {'dbname': dbname, 'row_factory': psycopg.rows.dict_row}
        if self.db_host:
            dbargs['host'] = self.db_host
        if self.db_port:
            dbargs['port'] = self.db_port
        if self.db_user:
            dbargs['user'] = self.db_user
        if self.db_pass:
            dbargs['password'] = self.db_pass
        return psycopg.connect(**dbargs)


    def write_nominatim_config(self, dbname):
        """ Set up a custom test configuration that connects to the given
            database. This sets up the environment variables so that they can
            be picked up by dotenv and creates a project directory with the
            appropriate website scripts.
        """
        if dbname.startswith('sqlite:'):
            dsn = 'sqlite:dbname={}'.format(dbname[7:])
        else:
            dsn = 'pgsql:dbname={}'.format(dbname)
        if self.db_host:
            dsn += ';host=' + self.db_host
        if self.db_port:
            dsn += ';port=' + self.db_port
        if self.db_user:
            dsn += ';user=' + self.db_user
        if self.db_pass:
            dsn += ';password=' + self.db_pass

        self.test_env = dict(self.default_config)
        self.test_env['NOMINATIM_DATABASE_DSN'] = dsn
        self.test_env['NOMINATIM_LANGUAGES'] = 'en,de,fr,ja'
        self.test_env['NOMINATIM_FLATNODE_FILE'] = ''
        self.test_env['NOMINATIM_IMPORT_STYLE'] = 'full'
        self.test_env['NOMINATIM_USE_US_TIGER_DATA'] = 'yes'
        self.test_env['NOMINATIM_DATADIR'] = str((self.src_dir / 'data').resolve())
        self.test_env['NOMINATIM_SQLDIR'] = str((self.src_dir / 'lib-sql').resolve())
        self.test_env['NOMINATIM_CONFIGDIR'] = str((self.src_dir / 'settings').resolve())
        if self.tokenizer is not None:
            self.test_env['NOMINATIM_TOKENIZER'] = self.tokenizer
        if self.import_style is not None:
            self.test_env['NOMINATIM_IMPORT_STYLE'] = self.import_style

        if self.server_module_path:
            self.test_env['NOMINATIM_DATABASE_MODULE_PATH'] = self.server_module_path

        if self.website_dir is not None:
            self.website_dir.cleanup()

        self.website_dir = tempfile.TemporaryDirectory()


    def get_test_config(self):
        cfg = Configuration(Path(self.website_dir.name), environ=self.test_env)
        cfg.set_libdirs(module=self.server_module_path)
        return cfg

    def get_libpq_dsn(self):
        dsn = self.test_env['NOMINATIM_DATABASE_DSN']

        def quote_param(param):
            key, val = param.split('=')
            val = val.replace('\\', '\\\\').replace("'", "\\'")
            if ' ' in val:
                val = "'" + val + "'"
            return key + '=' + val

        if dsn.startswith('pgsql:'):
            # Old PHP DSN format. Convert before returning.
            return ' '.join([quote_param(p) for p in dsn[6:].split(';')])

        return dsn


    def db_drop_database(self, name):
        """ Drop the database with the given name.
        """
        with self.connect_database('postgres') as conn:
            conn.autocommit = True
            conn.execute(pysql.SQL('DROP DATABASE IF EXISTS')
                         +  pysql.Identifier(name))

    def setup_template_db(self):
        """ Setup a template database that already contains common test data.
            Having a template database speeds up tests considerably but at
            the price that the tests sometimes run with stale data.
        """
        if self.template_db_done:
            return

        self.template_db_done = True

        self.write_nominatim_config(self.template_db)

        if not self._reuse_or_drop_db(self.template_db):
            try:
                # execute nominatim import on an empty file to get the right tables
                with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.xml') as fd:
                    fd.write(b'<osm version="0.6"></osm>')
                    fd.flush()
                    self.run_nominatim('import', '--osm-file', fd.name,
                                                 '--osm2pgsql-cache', '1',
                                                 '--ignore-errors',
                                                 '--offline', '--index-noanalyse')
            except:
                self.db_drop_database(self.template_db)
                raise

        self.run_nominatim('refresh', '--functions')


    def setup_api_db(self):
        """ Setup a test against the API test database.
        """
        self.write_nominatim_config(self.api_test_db)

        if self.api_test_db.startswith('sqlite:'):
            return

        if not self.api_db_done:
            self.api_db_done = True

            if not self._reuse_or_drop_db(self.api_test_db):
                testdata = (Path(__file__) / '..' / '..' / '..' / 'testdb').resolve()
                self.test_env['NOMINATIM_WIKIPEDIA_DATA_PATH'] = str(testdata)
                simp_file = Path(self.website_dir.name) / 'secondary_importance.sql.gz'
                simp_file.symlink_to(testdata / 'secondary_importance.sql.gz')

                try:
                    self.run_nominatim('import', '--osm-file', str(self.api_test_file))
                    self.run_nominatim('add-data', '--tiger-data', str(testdata / 'tiger'))
                    self.run_nominatim('freeze')

                    if self.tokenizer == 'legacy':
                        phrase_file = str(testdata / 'specialphrases_testdb.sql')
                        run_script(['psql', '-d', self.api_test_db, '-f', phrase_file])
                    else:
                        csv_path = str(testdata / 'full_en_phrases_test.csv')
                        self.run_nominatim('special-phrases', '--import-from-csv', csv_path)
                except:
                    self.db_drop_database(self.api_test_db)
                    raise

        tokenizer_factory.get_tokenizer_for_db(self.get_test_config())


    def setup_unknown_db(self):
        """ Setup a test against a non-existing database.
        """
        # The tokenizer needs an existing database to function.
        # So start with the usual database
        class _Context:
            db = None

        context = _Context()
        self.setup_db(context)
        tokenizer_factory.create_tokenizer(self.get_test_config(), init_db=False)

        # Then drop the DB again
        self.teardown_db(context, force_drop=True)

    def setup_db(self, context):
        """ Setup a test against a fresh, empty test database.
        """
        self.setup_template_db()
        with self.connect_database(self.template_db) as conn:
            conn.autocommit = True
            conn.execute(pysql.SQL('DROP DATABASE IF EXISTS')
                                   + pysql.Identifier(self.test_db))
            conn.execute(pysql.SQL('CREATE DATABASE {} TEMPLATE = {}').format(
                           pysql.Identifier(self.test_db),
                           pysql.Identifier(self.template_db)))

        self.write_nominatim_config(self.test_db)
        context.db = self.connect_database(self.test_db)
        context.db.autocommit = True
        register_hstore(context.db)

    def teardown_db(self, context, force_drop=False):
        """ Remove the test database, if it exists.
        """
        if hasattr(context, 'db'):
            context.db.close()

        if force_drop or not self.keep_scenario_db:
            self.db_drop_database(self.test_db)

    def _reuse_or_drop_db(self, name):
        """ Check for the existence of the given DB. If reuse is enabled,
            then the function checks for existnce and returns True if the
            database is already there. Otherwise an existing database is
            dropped and always false returned.
        """
        if self.reuse_template:
            with self.connect_database('postgres') as conn:
                num = execute_scalar(conn,
                                     'select count(*) from pg_database where datname = %s',
                                     (name,))
                if num == 1:
                    return True
        else:
            self.db_drop_database(name)

        return False


    def reindex_placex(self, db):
        """ Run the indexing step until all data in the placex has
            been processed. Indexing during updates can produce more data
            to index under some circumstances. That is why indexing may have
            to be run multiple times.
        """
        self.run_nominatim('index')


    def run_nominatim(self, *cmdline):
        """ Run the nominatim command-line tool via the library.
        """
        if self.website_dir is not None:
            cmdline = list(cmdline) + ['--project-dir', self.website_dir.name]

        cli.nominatim(module_dir=self.server_module_path,
                      osm2pgsql_path=None,
                      cli_args=cmdline,
                      environ=self.test_env)


    def copy_from_place(self, db):
        """ Copy data from place to the placex and location_property_osmline
            tables invoking the appropriate triggers.
        """
        self.run_nominatim('refresh', '--functions', '--no-diff-updates')

        with db.cursor() as cur:
            cur.execute("""INSERT INTO placex (osm_type, osm_id, class, type,
                                               name, admin_level, address,
                                               extratags, geometry)
                             SELECT osm_type, osm_id, class, type,
                                    name, admin_level, address,
                                    extratags, geometry
                               FROM place
                               WHERE not (class='place' and type='houses' and osm_type='W')""")
            cur.execute("""INSERT INTO location_property_osmline (osm_id, address, linegeo)
                             SELECT osm_id, address, geometry
                               FROM place
                              WHERE class='place' and type='houses'
                                    and osm_type='W'
                                    and ST_GeometryType(geometry) = 'ST_LineString'""")


    def create_api_request_func_starlette(self):
        import nominatim_api.server.starlette.server
        from asgi_lifespan import LifespanManager
        import httpx

        async def _request(endpoint, params, project_dir, environ, http_headers):
            app = nominatim_api.server.starlette.server.get_application(project_dir, environ)

            async with LifespanManager(app):
                async with httpx.AsyncClient(app=app, base_url="http://nominatim.test") as client:
                    response = await client.get(f"/{endpoint}", params=params,
                                                headers=http_headers)

            return response.text, response.status_code

        return _request


    def create_api_request_func_falcon(self):
        import nominatim_api.server.falcon.server
        import falcon.testing

        async def _request(endpoint, params, project_dir, environ, http_headers):
            app = nominatim_api.server.falcon.server.get_application(project_dir, environ)

            async with falcon.testing.ASGIConductor(app) as conductor:
                response = await conductor.get(f"/{endpoint}", params=params,
                                               headers=http_headers)

            return response.text, response.status_code

        return _request



