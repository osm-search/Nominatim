from lettuce import *
from nose.tools import *
import logging
import os
import subprocess
import psycopg2
import re
from haversine import haversine
from shapely.wkt import loads as wkt_load
from shapely.ops import linemerge

logger = logging.getLogger(__name__)

class NominatimConfig:

    def __init__(self):
        # logging setup
        loglevel = getattr(logging, os.environ.get('LOGLEVEL','info').upper())
        if 'LOGFILE' in os.environ:
            logging.basicConfig(filename=os.environ.get('LOGFILE','run.log'),
                                level=loglevel)
        else:
            logging.basicConfig(level=loglevel)
        # Nominatim test setup
        self.base_url = os.environ.get('NOMINATIM_SERVER', 'http://localhost/nominatim')
        self.source_dir = os.path.abspath(os.environ.get('NOMINATIM_DIR', '..'))
        self.template_db = os.environ.get('TEMPLATE_DB', 'test_template_nominatim')
        self.test_db = os.environ.get('TEST_DB', 'test_nominatim')
        self.local_settings_file = os.environ.get('NOMINATIM_SETTINGS', '/tmp/nominatim_settings.php')
        self.reuse_template = 'NOMINATIM_REMOVE_TEMPLATE' not in os.environ
        self.keep_scenario_db = 'NOMINATIM_KEEP_SCENARIO_DB' in os.environ
        os.environ['NOMINATIM_SETTINGS'] = '/tmp/nominatim_settings.php'

        scriptpath = os.path.dirname(os.path.abspath(__file__))
        self.scene_path = os.environ.get('SCENE_PATH', 
                os.path.join(scriptpath, '..', 'scenes', 'data'))


    def __str__(self):
        return 'Server URL: %s\nSource dir: %s\n' % (self.base_url, self.source_dir)

world.config = NominatimConfig()

@world.absorb
def write_nominatim_config(dbname):
    f = open(world.config.local_settings_file, 'w')
    f.write("<?php\n  @define('CONST_Database_DSN', 'pgsql://@/%s');\n" % dbname)
    f.close()


@world.absorb
def run_nominatim_script(script, *args):
    cmd = [os.path.join(world.config.source_dir, 'utils', '%s.php' % script)]
    cmd.extend(['--%s' % x for x in args])
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (outp, outerr) = proc.communicate()
    assert (proc.returncode == 0), "Script '%s' failed:\n%s\n%s\n" % (script, outp, outerr)

@world.absorb
def make_hash(inp):
    return eval('{' + inp + '}')

@world.absorb
def split_id(oid):
    """ Splits a unique identifier for places into its components.
        As place_ids cannot be used for testing, we use a unique
        identifier instead that is of the form <osmtype><osmid>[:class].
    """
    oid = oid.strip()
    if oid == 'None':
        return None, None, None
    osmtype = oid[0]
    assert_in(osmtype, ('R','N','W'))
    if ':' in oid:
        osmid, cls = oid[1:].split(':')
        return (osmtype, int(osmid), cls)
    else:
        return (osmtype, int(oid[1:]), None)

@world.absorb
def get_placeid(oid):
    """ Tries to retrive the place_id for a unique identifier. """
    if oid[0].isdigit():
        return int(oid)

    osmtype, osmid, cls = world.split_id(oid)
    if osmtype is None:
        return None
    cur = world.conn.cursor()
    if cls is None:
        q = 'SELECT place_id FROM placex where osm_type = %s and osm_id = %s'
        params = (osmtype, osmid)
    else:
        q = 'SELECT place_id FROM placex where osm_type = %s and osm_id = %s and class = %s'
        params = (osmtype, osmid, cls)
    cur.execute(q, params)
    assert_equals (cur.rowcount, 1)
    return cur.fetchone()[0]


@world.absorb
def match_geometry(coord, matchstring):
    m = re.match(r'([-0-9.]+),\s*([-0-9.]+)\s*(?:\+-([0-9.]+)([a-z]+)?)?', matchstring)
    assert_is_not_none(m, "Invalid match string")

    logger.debug("Distmatch: %s/%s %s %s" % (m.group(1), m.group(2), m.group(3), m.group(4) ))
    dist = haversine(coord, (float(m.group(1)), float(m.group(2))))

    if m.group(3) is not None:
        expdist = float(m.group(3))
        if m.group(4) is not None:
            if m.group(4) == 'm':
                expdist = expdist/1000
            elif m.group(4) == 'km':
                pass
            else:
                raise Exception("Unknown unit '%s' in geometry match" % (m.group(4), ))
    else:
        expdist = 0

    logger.debug("Distances expected: %f, got: %f" % (expdist, dist))
    assert dist <= expdist, "Geometry too far away, expected: %f, got: %f" % (expdist, dist)



@world.absorb
def db_dump_table(table):
    cur = world.conn.cursor()
    cur.execute('SELECT * FROM %s' % table)
    print '<<<<<<< BEGIN OF TABLE DUMP %s' % table
    for res in cur:
            print res
    print '<<<<<<< END OF TABLE DUMP %s' % table

@world.absorb
def db_drop_database(name):
    conn = psycopg2.connect(database='postgres')
    conn.set_isolation_level(0)
    cur = conn.cursor()
    cur.execute('DROP DATABASE IF EXISTS %s' % (name, ))
    conn.close()


world.is_template_set_up = False

@world.absorb
def db_template_setup():
    """ Set up a template database, containing all tables
        but not yet any functions.
    """
    if world.is_template_set_up:
        return

    world.is_template_set_up = True
    world.write_nominatim_config(world.config.template_db)
    if world.config.reuse_template:
        # check that the template is there
        conn = psycopg2.connect(database='postgres')
        cur = conn.cursor()
        cur.execute('select count(*) from pg_database where datname = %s', 
                     (world.config.template_db,))
        if cur.fetchone()[0] == 1:
            return
    else:
        # just in case... make sure a previous table has been dropped
        world.db_drop_database(world.config.template_db)
    # call the first part of database setup
    world.run_nominatim_script('setup', 'create-db', 'setup-db')
    # remove external data to speed up indexing for tests
    conn = psycopg2.connect(database=world.config.template_db)
    psycopg2.extras.register_hstore(conn, globally=False, unicode=True)
    cur = conn.cursor()
    for table in ('gb_postcode', 'us_postcode', 'us_state', 'us_statecounty'):
        cur.execute('TRUNCATE TABLE %s' % (table,))
    conn.commit()
    conn.close()
    # execute osm2pgsql on an empty file to get the right tables
    osm2pgsql = os.path.join(world.config.source_dir, 'osm2pgsql', 'osm2pgsql')
    proc = subprocess.Popen([osm2pgsql, '-lsc', '-O', 'gazetteer', '-d', world.config.template_db, '-'],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    [outstr, errstr] = proc.communicate(input='<osm version="0.6"></osm>')
    world.run_nominatim_script('setup', 'create-functions', 'create-tables', 'create-partition-tables', 'create-partition-functions', 'load-data', 'create-search-indices')


# Leave the table around so it can be reused again after a non-reuse test round.
#@after.all
def db_template_teardown(total):
    """ Set up a template database, containing all tables
        but not yet any functions.
    """
    if world.is_template_set_up:
        # remove template DB
        if not world.config.reuse_template:
            world.db_drop_database(world.config.template_db)
        try:
            os.remove(world.config.local_settings_file)
        except OSError:
            pass # ignore missing file


##########################################################################
#
# Data scene handling
#

world.scenes = {}
world.current_scene = None

@world.absorb
def load_scene(name):
    if name in world.scenes:
        world.current_scene = world.scenes[name]
    else:
        with open(os.path.join(world.config.scene_path, "%s.wkt" % name), 'r') as fd:
            scene = {}
            for line in fd:
                if line.strip():
                    obj, wkt = line.split('|', 2)
                    wkt = wkt.strip()
                    scene[obj.strip()] = wkt_load(wkt)
            world.scenes[name] = scene
            world.current_scene = scene

@world.absorb
def get_scene_geometry(name):
    if not ':' in name:
        # Not a scene description
        return None
    
    geoms = []
    for obj in name.split('+'):
        oname = obj.strip()
        if oname.startswith(':'):
            geoms.append(world.current_scene[oname[1:]])
        else:
            scene, obj = oname.split(':', 2)
            oldscene = world.current_scene
            world.load_scene(scene)
            wkt = world.current_scene[obj]
            world.current_scene = oldscene
            geoms.append(wkt)

    if len(geoms) == 1:
        return geoms[0]
    else:
        return linemerge(geoms)
