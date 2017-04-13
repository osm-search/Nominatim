from behave import *
import logging
import os
import psycopg2
import psycopg2.extras
import subprocess
import tempfile
from nose.tools import * # for assert functions
from sys import version_info as python_version

logger = logging.getLogger(__name__)

userconfig = {
    'BUILDDIR' : os.path.join(os.path.split(__file__)[0], "../../build"),
    'REMOVE_TEMPLATE' : False,
    'KEEP_TEST_DB' : False,
    'TEMPLATE_DB' : 'test_template_nominatim',
    'TEST_DB' : 'test_nominatim',
    'API_TEST_DB' : 'test_api_nominatim',
    'TEST_SETTINGS_FILE' : '/tmp/nominatim_settings.php'
}

use_step_matcher("re")

class NominatimEnvironment(object):
    """ Collects all functions for the execution of Nominatim functions.
    """

    def __init__(self, config):
        self.build_dir = os.path.abspath(config['BUILDDIR'])
        self.template_db = config['TEMPLATE_DB']
        self.test_db = config['TEST_DB']
        self.api_test_db = config['API_TEST_DB']
        self.local_settings_file = config['TEST_SETTINGS_FILE']
        self.reuse_template = not config['REMOVE_TEMPLATE']
        self.keep_scenario_db = config['KEEP_TEST_DB']
        os.environ['NOMINATIM_SETTINGS'] = self.local_settings_file

        self.template_db_done = False

    def write_nominatim_config(self, dbname):
        f = open(self.local_settings_file, 'w')
        f.write("<?php\n  @define('CONST_Database_DSN', 'pgsql://@/%s');\n" % dbname)
        f.write("@define('CONST_Osm2pgsql_Flatnode_File', null);\n")
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

        # execute osm2pgsql import on an empty file to get the right tables
        with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.xml') as fd:
            fd.write(b'<osm version="0.6"></osm>')
            fd.flush()
            self.run_setup_script('import-data',
                                  'ignore-errors',
                                  'create-functions',
                                  'create-tables',
                                  'create-partition-tables',
                                  'create-partition-functions',
                                  'load-data',
                                  'create-search-indices',
                                  osm_file=fd.name,
                                  osm2pgsql_cache='200')

    def setup_api_db(self, context):
        self.write_nominatim_config(self.api_test_db)

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

    def run_setup_script(self, *args, **kwargs):
        self.run_nominatim_script('setup', *args, **kwargs)

    def run_update_script(self, *args, **kwargs):
        self.run_nominatim_script('update', *args, **kwargs)

    def run_nominatim_script(self, script, *args, **kwargs):
        cmd = [os.path.join(self.build_dir, 'utils', '%s.php' % script)]
        cmd.extend(['--%s' % x for x in args])
        for k, v in kwargs.items():
            cmd.extend(('--' + k.replace('_', '-'), str(v)))
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
        self.scene_cache = {}
        self.clear_grid()

    def parse_geometry(self, geom, scene):
        if geom.find(':') >= 0:
            return "ST_SetSRID(%s, 4326)" % self.get_scene_geometry(scene, geom)

        if geom.find(',') < 0:
            out = "POINT(%s)" % self.mk_wkt_point(geom)
        elif geom.find('(') < 0:
            line = ','.join([self.mk_wkt_point(x) for x in geom.split(',')])
            out = "LINESTRING(%s)" % line
        else:
            inner = geom.strip('() ')
            line = ','.join([self.mk_wkt_point(x) for x in inner.split(',')])
            out = "POLYGON((%s))" % line

        return "ST_SetSRID('%s'::geometry, 4326)" % out

    def mk_wkt_point(self, point):
        geom = point.strip()
        if geom.find(' ') >= 0:
            return geom
        else:
            pt = self.grid_node(int(geom))
            assert_is_not_none(pt, "Point not found in grid")
            return "%f %f" % pt

    def get_scene_geometry(self, default_scene, name):
        geoms = []
        for obj in name.split('+'):
            oname = obj.strip()
            if oname.startswith(':'):
                assert_is_not_none(default_scene, "You need to set a scene")
                defscene = self.load_scene(default_scene)
                wkt = defscene[oname[1:]]
            else:
                scene, obj = oname.split(':', 2)
                scene_geoms = self.load_scene(scene)
                wkt = scene_geoms[obj]

            geoms.append("'%s'::geometry" % wkt)

        if len(geoms) == 1:
            return geoms[0]
        else:
            return 'ST_LineMerge(ST_Collect(ARRAY[%s]))' % ','.join(geoms)

    def load_scene(self, name):
        if name in self.scene_cache:
            return self.scene_cache[name]

        scene = {}
        with open(os.path.join(self.scene_path, "%s.wkt" % name), 'r') as fd:
            for line in fd:
                if line.strip():
                    obj, wkt = line.split('|', 2)
                    scene[obj.strip()] = wkt.strip()
            self.scene_cache[name] = scene

        return scene

    def clear_grid(self):
        self.grid = {}

    def add_grid_node(self, nodeid, x, y):
        self.grid[nodeid] = (x, y)

    def grid_node(self, nodeid):
        return self.grid.get(nodeid)


def before_all(context):
    # logging setup
    context.config.setup_logging()
    # set up -D options
    for k,v in userconfig.items():
        context.config.userdata.setdefault(k, v)
    logging.debug('User config: %s' %(str(context.config.userdata)))
    # Nominatim test setup
    context.nominatim = NominatimEnvironment(context.config.userdata)
    context.osm = OSMDataFactory()

def after_all(context):
    context.nominatim.cleanup()


def before_scenario(context, scenario):
    if 'DB' in context.tags:
        context.nominatim.setup_db(context)
    elif 'APIDB' in context.tags:
        context.nominatim.setup_api_db(context)
    context.scene = None

def after_scenario(context, scenario):
    if 'DB' in context.tags:
        context.nominatim.teardown_db(context)

