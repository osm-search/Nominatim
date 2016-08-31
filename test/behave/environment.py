from behave import *
import logging
import os
import psycopg2
import psycopg2.extras
import subprocess
from sys import version_info as python_version

logger = logging.getLogger(__name__)

userconfig = {
    'BASEURL' : 'http://localhost/nominatim',
    'BUILDDIR' : '../build',
    'REMOVE_TEMPLATE' : False,
    'KEEP_TEST_DB' : False,
    'TEMPLATE_DB' : 'test_template_nominatim',
    'TEST_DB' : 'test_nominatim',
    'TEST_SETTINGS_FILE' : '/tmp/nominatim_settings.php'
}

class NominatimEnvironment(object):
    """ Collects all functions for the execution of Nominatim functions.
    """

    def __init__(self, config):
        self.build_dir = os.path.abspath(config['BUILDDIR'])
        self.template_db = config['TEMPLATE_DB']
        self.test_db = config['TEST_DB']
        self.local_settings_file = config['TEST_SETTINGS_FILE']
        self.reuse_template = not config['REMOVE_TEMPLATE']
        self.keep_scenario_db = config['KEEP_TEST_DB']
        os.environ['NOMINATIM_SETTINGS'] = self.local_settings_file

        self.template_db_done = False

    def write_nominatim_config(self, dbname):
        f = open(self.local_settings_file, 'w')
        f.write("<?php\n  @define('CONST_Database_DSN', 'pgsql://@/%s');\n" % dbname)
        f.close()

    def cleanup(self):
        try:
            os.remove(self.local_settings_file)
        except OSError:
            pass # ignore missing file

    def db_drop_database(self, name):
        conn = psycopg2.connect(database='postgres')
        conn.set_isolation_level(0)
        cur = conn.cursor()
        cur.execute('DROP DATABASE IF EXISTS %s' % (name, ))
        conn.close()

    def setup_template_db(self):
        if self.template_db_done:
            return

        self.template_db_done = True

        if self.reuse_template:
            # check that the template is there
            conn = psycopg2.connect(database='postgres')
            cur = conn.cursor()
            cur.execute('select count(*) from pg_database where datname = %s',
                        (self.template_db,))
            if cur.fetchone()[0] == 1:
                return
            conn.close()
        else:
            # just in case... make sure a previous table has been dropped
            self.db_drop_database(self.template_db)

        # call the first part of database setup
        self.write_nominatim_config(self.template_db)
        self.run_setup_script('create-db', 'setup-db')
        # remove external data to speed up indexing for tests
        conn = psycopg2.connect(database=self.template_db)
        cur = conn.cursor()
        cur.execute("""select tablename from pg_tables
                       where tablename in ('gb_postcode', 'us_postcode')""")
        for t in cur:
            conn.cursor().execute('TRUNCATE TABLE %s' % (t[0],))
        conn.commit()
        conn.close()

        # execute osm2pgsql on an empty file to get the right tables
        osm2pgsql = os.path.join(self.build_dir, 'osm2pgsql', 'osm2pgsql')
        proc = subprocess.Popen([osm2pgsql, '-lsc', '-r', 'xml',
                                 '-O', 'gazetteer', '-d', self.template_db, '-'],
                                cwd=self.build_dir, stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        [outstr, errstr] = proc.communicate(input=b'<osm version="0.6"></osm>')
        logger.debug("running osm2pgsql for template: %s\n%s\n%s" % (osm2pgsql, outstr, errstr))
        self.run_setup_script('create-functions', 'create-tables',
                              'create-partition-tables', 'create-partition-functions',
                              'load-data', 'create-search-indices')



    def setup_db(self, context):
        self.setup_template_db()
        self.write_nominatim_config(self.test_db)
        conn = psycopg2.connect(database=self.template_db)
        conn.set_isolation_level(0)
        cur = conn.cursor()
        cur.execute('DROP DATABASE IF EXISTS %s' % (self.test_db, ))
        cur.execute('CREATE DATABASE %s TEMPLATE = %s' % (self.test_db, self.template_db))
        conn.close()
        context.db = psycopg2.connect(database=self.test_db)
        if python_version[0] < 3:
            psycopg2.extras.register_hstore(context.db, globally=False, unicode=True)
        else:
            psycopg2.extras.register_hstore(context.db, globally=False)

    def teardown_db(self, context):
        if 'db' in context:
            context.db.close()

        if not self.keep_scenario_db:
            self.db_drop_database(self.test_db)

    def run_setup_script(self, *args):
        self.run_nominatim_script('setup', *args)

    def run_nominatim_script(self, script, *args):
        cmd = [os.path.join(self.build_dir, 'utils', '%s.php' % script)]
        cmd.extend(['--%s' % x for x in args])
        proc = subprocess.Popen(cmd, cwd=self.build_dir,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (outp, outerr) = proc.communicate()
        logger.debug("run_nominatim_script: %s\n%s\n%s" % (cmd, outp, outerr))
        assert (proc.returncode == 0), "Script '%s' failed:\n%s\n%s\n" % (script, outp, outerr)


class OSMDataFactory(object):

    def __init__(self):
        scriptpath = os.path.dirname(os.path.abspath(__file__))
        self.scene_path = os.environ.get('SCENE_PATH',
                           os.path.join(scriptpath, '..', 'scenes', 'data'))


def before_all(context):
    for k,v in userconfig.items():
        context.config.userdata.setdefault(k, v)
    print('config:', context.config.userdata)
    # logging setup
    context.config.setup_logging()
    # Nominatim test setup
    context.nominatim = NominatimEnvironment(context.config.userdata)
    context.osm = OSMDataFactory()

def after_all(context):
    context.nominatim.cleanup()


def before_scenario(context, scenario):
    if 'DB' in context.tags:
        context.nominatim.setup_db(context)

def after_scenario(context, scenario):
    if 'DB' in context.tags:
        context.nominatim.teardown_db(context)

