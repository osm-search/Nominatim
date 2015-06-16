""" Steps for setting up a test database with imports and updates.

    There are two ways to state geometries for test data: with coordinates
    and via scenes.

    Coordinates should be given as a wkt without the enclosing type name.

    Scenes are prepared geometries which can be found in the scenes/data/
    directory. Each scene is saved in a .wkt file with its name, which
    contains a list of id/wkt pairs. A scene can be set globally
    for a scene by using the step `the scene <scene name>`. Then each
    object should be refered to as `:<object id>`. A geometry can also
    be referred to without loading the scene by explicitly stating the
    scene: `<scene name>:<object id>`.
"""

from nose.tools import *
from lettuce import *
import psycopg2
import psycopg2.extensions
import psycopg2.extras
import os
import subprocess
import random
import base64

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

@before.each_scenario
def setup_test_database(scenario):
    """ Creates a new test database from the template database
        that was set up earlier in terrain.py. Will be done only
        for scenarios whose feature is tagged with 'DB'.
    """
    if scenario.feature.tags is not None and 'DB' in scenario.feature.tags:
        world.db_template_setup()
        world.write_nominatim_config(world.config.test_db)
        conn = psycopg2.connect(database=world.config.template_db)
        conn.set_isolation_level(0)
        cur = conn.cursor()
        cur.execute('DROP DATABASE IF EXISTS %s' % (world.config.test_db, ))
        cur.execute('CREATE DATABASE %s TEMPLATE = %s' % (world.config.test_db, world.config.template_db))
        conn.close()
        world.conn = psycopg2.connect(database=world.config.test_db)
        psycopg2.extras.register_hstore(world.conn, globally=False, unicode=True)

@step('a wiped database')
def db_setup_wipe_db(step):
    """Explicit DB scenario setup only needed
       to work around a bug where scenario outlines don't call
       before_each_scenario correctly.
    """
    if hasattr(world, 'conn'):
        world.conn.close()
    conn = psycopg2.connect(database=world.config.template_db)
    conn.set_isolation_level(0)
    cur = conn.cursor()
    cur.execute('DROP DATABASE IF EXISTS %s' % (world.config.test_db, ))
    cur.execute('CREATE DATABASE %s TEMPLATE = %s' % (world.config.test_db, world.config.template_db))
    conn.close()
    world.conn = psycopg2.connect(database=world.config.test_db)
    psycopg2.extras.register_hstore(world.conn, globally=False, unicode=True)


@after.each_scenario
def tear_down_test_database(scenario):
    """ Drops any previously created test database.
    """
    if hasattr(world, 'conn'):
        world.conn.close()
    if scenario.feature.tags is not None and 'DB' in scenario.feature.tags and not world.config.keep_scenario_db:
        conn = psycopg2.connect(database=world.config.template_db)
        conn.set_isolation_level(0)
        cur = conn.cursor()
        cur.execute('DROP DATABASE %s' % (world.config.test_db,))
        conn.close()


def _format_placex_cols(cols, geomtype, force_name):
    if 'name' in cols:
        if cols['name'].startswith("'"):
            cols['name'] = world.make_hash(cols['name'])
        else:
            cols['name'] = { 'name' : cols['name'] }
    elif force_name:
        cols['name'] = { 'name' : base64.urlsafe_b64encode(os.urandom(int(random.random()*30))) }
    if 'extratags' in cols:
        cols['extratags'] = world.make_hash(cols['extratags'])
    if 'admin_level' not in cols:
        cols['admin_level'] = 100
    if 'geometry' in cols:
        coords = world.get_scene_geometry(cols['geometry'])
        if coords is None:
            coords = "'%s(%s)'::geometry" % (geomtype, cols['geometry'])
        else:
            coords = "'%s'::geometry" % coords.wkt
        cols['geometry'] = coords
    for k in cols:
        if not cols[k]:
            cols[k] = None


def _insert_place_table_nodes(places, force_name):
    cur = world.conn.cursor()
    for line in places:
        cols = dict(line)
        cols['osm_type'] = 'N'
        _format_placex_cols(cols, 'POINT', force_name)
        if 'geometry' in cols:
            coords = cols.pop('geometry')
        else:
            coords = "ST_Point(%f, %f)" % (random.random()*360 - 180, random.random()*180 - 90)

        query = 'INSERT INTO place (%s,geometry) values(%s, ST_SetSRID(%s, 4326))' % (
              ','.join(cols.iterkeys()),
              ','.join(['%s' for x in range(len(cols))]),
              coords
             )
        cur.execute(query, cols.values())
    world.conn.commit()


def _insert_place_table_objects(places, geomtype, force_name):
    cur = world.conn.cursor()
    for line in places:
        cols = dict(line)
        if 'osm_type' not in cols:
            cols['osm_type'] = 'W'
        _format_placex_cols(cols, geomtype, force_name)
        coords = cols.pop('geometry')

        query = 'INSERT INTO place (%s, geometry) values(%s, ST_SetSRID(%s, 4326))' % (
              ','.join(cols.iterkeys()),
              ','.join(['%s' for x in range(len(cols))]),
              coords
             )
        cur.execute(query, cols.values())
    world.conn.commit()

@step(u'the scene (.*)')
def import_set_scene(step, scene):
    world.load_scene(scene)

@step(u'the (named )?place (node|way|area)s')
def import_place_table_nodes(step, named, osmtype):
    """Insert a list of nodes into the placex table.
       Expects a table where columns are named in the same way as placex.
    """
    cur = world.conn.cursor()
    cur.execute('ALTER TABLE place DISABLE TRIGGER place_before_insert')
    if osmtype == 'node':
        _insert_place_table_nodes(step.hashes, named is not None)
    elif osmtype == 'way' :
        _insert_place_table_objects(step.hashes, 'LINESTRING', named is not None)
    elif osmtype == 'area' :
        _insert_place_table_objects(step.hashes, 'POLYGON', named is not None)
    cur.execute('ALTER TABLE place ENABLE TRIGGER place_before_insert')
    cur.close()
    world.conn.commit()


@step(u'the relations')
def import_fill_planet_osm_rels(step):
    """Adds a raw relation to the osm2pgsql table.
       Three columns need to be suplied: id, tags, members.
    """
    cur = world.conn.cursor()
    for line in step.hashes:
        members = []
        parts = { 'n' : [], 'w' : [], 'r' : [] }
        if line['members'].strip():
            for mem in line['members'].split(','):
                memparts = mem.strip().split(':', 2)
                memid = memparts[0].lower()
                parts[memid[0]].append(int(memid[1:]))
                members.append(memid)
                if len(memparts) == 2:
                    members.append(memparts[1])
                else:
                    members.append('')
        tags = []
        for k,v in world.make_hash(line['tags']).iteritems():
            tags.extend((k,v))
        if not members:
            members = None

        cur.execute("""INSERT INTO planet_osm_rels 
                      (id, way_off, rel_off, parts, members, tags, pending)
                      VALUES (%s, %s, %s, %s, %s, %s, false)""",
                   (line['id'], len(parts['n']), len(parts['n']) + len(parts['w']),
                   parts['n'] + parts['w'] + parts['r'], members, tags))
    world.conn.commit()
        

@step(u'the ways')
def import_fill_planet_osm_ways(step):
    cur = world.conn.cursor()
    for line in step.hashes:
        if 'tags' in line:
            tags = world.make_hash(line['tags'])
        else:
            tags = None
        nodes = [int(x.strip()) for x in line['nodes'].split(',')]

        cur.execute("""INSERT INTO planet_osm_ways
                       (id, nodes, tags, pending)
                       VALUES (%s, %s, %s, false)""",
                    (line['id'], nodes, tags))
    world.conn.commit()

############### import and update steps #######################################

@step(u'importing')
def import_database(step):
    """ Runs the actual indexing. """
    world.run_nominatim_script('setup', 'create-functions', 'create-partition-functions')
    cur = world.conn.cursor()
    cur.execute("""insert into placex (osm_type, osm_id, class, type, name, admin_level,
                   housenumber, street, addr_place, isin, postcode, country_code, extratags,
                   geometry) select * from place""")
    world.conn.commit()
    world.run_nominatim_script('setup', 'index', 'index-noanalyse')
    #world.db_dump_table('placex')


@step(u'updating place (node|way|area)s')
def update_place_table_nodes(step, osmtype):
    """ Replace a geometry in place by reinsertion and reindex database.
    """
    world.run_nominatim_script('setup', 'create-functions', 'create-partition-functions', 'enable-diff-updates')
    if osmtype == 'node':
        _insert_place_table_nodes(step.hashes, False)
    elif osmtype == 'way':
        _insert_place_table_objects(step.hashes, 'LINESTRING', False)
    elif osmtype == 'area':
        _insert_place_table_objects(step.hashes, 'POLYGON', False)
    world.run_nominatim_script('update', 'index')

@step(u'marking for delete (.*)')
def update_delete_places(step, places):
    """ Remove an entry from place and reindex database.
    """
    world.run_nominatim_script('setup', 'create-functions', 'create-partition-functions', 'enable-diff-updates')
    cur = world.conn.cursor()
    for place in places.split(','):
        osmtype, osmid, cls = world.split_id(place)
        if cls is None:
            q = "delete from place where osm_type = %s and osm_id = %s"
            params = (osmtype, osmid)
        else:
            q = "delete from place where osm_type = %s and osm_id = %s and class = %s"
            params = (osmtype, osmid, cls)
        cur.execute(q, params)
    world.conn.commit()
    #world.db_dump_table('placex')
    world.run_nominatim_script('update', 'index')



@step(u'sending query "(.*)"( with dups)?$')
def query_cmd(step, query, with_dups):
    """ Results in standard query output. The same tests as for API queries
        can be used.
    """
    cmd = [os.path.join(world.config.source_dir, 'utils', 'query.php'),
           '--search', query]
    if with_dups is not None:
        cmd.append('--nodedupe')
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (outp, err) = proc.communicate()
    assert (proc.returncode == 0), "query.php failed with message: %s" % err
    world.page = outp
    world.response_format = 'json'   
    world.returncode = 200

