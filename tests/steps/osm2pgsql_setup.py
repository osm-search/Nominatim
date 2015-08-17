""" Steps for setting up a test database for osm2pgsql import.

    Note that osm2pgsql features need a database and therefore need
    to be tagged with @DB.
"""

from nose.tools import *
from lettuce import *

import logging
import random
import tempfile
import os
import subprocess

logger = logging.getLogger(__name__)

@before.each_scenario
def osm2pgsql_setup_test(scenario):
    world.osm2pgsql = []

@step(u'the osm nodes:')
def osm2pgsql_import_nodes(step):
    """ Define a list of OSM nodes to be imported, given as a table.
        Each line describes one node with all its attributes.
        'id' is mendatory, all other fields are filled with random values
        when not given. If 'tags' is missing an empty tag list is assumed.
        For updates, a mandatory 'action' column needs to contain 'A' (add),
        'M' (modify), 'D' (delete).
    """
    for line in step.hashes:
        node = { 'type' : 'N', 'version' : '1', 'timestamp': "2012-05-01T15:06:20Z",  
                 'changeset' : "11470653", 'uid' : "122294", 'user' : "foo"
               }
        node.update(line)
        node['id'] = int(node['id'])
        if 'geometry' in node:
            lat, lon = node['geometry'].split(' ')
            node['lat'] = float(lat)
            node['lon'] = float(lon)
        else:
            node['lon'] = random.random()*360 - 180
            node['lat'] = random.random()*180 - 90
        if 'tags' in node:
            node['tags'] = world.make_hash(line['tags'])
        else:
            node['tags'] = {}

        world.osm2pgsql.append(node)


@step(u'the osm ways:')
def osm2pgsql_import_ways(step):
    """ Define a list of OSM ways to be imported.
    """
    for line in step.hashes:
        way = { 'type' : 'W', 'version' : '1', 'timestamp': "2012-05-01T15:06:20Z",  
                 'changeset' : "11470653", 'uid' : "122294", 'user' : "foo"
               }
        way.update(line)

        way['id'] = int(way['id'])
        if 'tags' in way:
            way['tags'] = world.make_hash(line['tags'])
        else:
            way['tags'] = None
        way['nodes'] = way['nodes'].strip().split()

        world.osm2pgsql.append(way)

membertype = { 'N' : 'node', 'W' : 'way', 'R' : 'relation' }

@step(u'the osm relations:')
def osm2pgsql_import_rels(step):
    """ Define a list of OSM relation to be imported.
    """
    for line in step.hashes:
        rel = { 'type' : 'R', 'version' : '1', 'timestamp': "2012-05-01T15:06:20Z",  
                 'changeset' : "11470653", 'uid' : "122294", 'user' : "foo"
               }
        rel.update(line)

        rel['id'] = int(rel['id'])
        if 'tags' in rel:
            rel['tags'] = world.make_hash(line['tags'])
        else:
            rel['tags'] = {}
        members = []
        if rel['members'].strip():
            for mem in line['members'].split(','):
                memparts = mem.strip().split(':', 2)
                memid = memparts[0].upper()
                members.append((membertype[memid[0]], 
                                memid[1:], 
                                memparts[1] if len(memparts) == 2 else ''
                              ))
        rel['members'] = members

        world.osm2pgsql.append(rel)



def _sort_xml_entries(x, y):
    if x['type'] == y['type']:
        return cmp(x['id'], y['id'])
    else:
        return cmp('NWR'.find(x['type']), 'NWR'.find(y['type']))

def write_osm_obj(fd, obj):
    if obj['type'] == 'N':
        fd.write('<node id="%(id)d" lat="%(lat).8f" lon="%(lon).8f" version="%(version)s" timestamp="%(timestamp)s" changeset="%(changeset)s" uid="%(uid)s" user="%(user)s"'% obj)
        if obj['tags'] is None:
            fd.write('/>\n')
        else:
            fd.write('>\n')
            for k,v in obj['tags'].iteritems():
                fd.write('  <tag k="%s" v="%s"/>\n' % (k, v))
            fd.write('</node>\n')
    elif obj['type'] == 'W':
        fd.write('<way id="%(id)d" version="%(version)s" changeset="%(changeset)s" timestamp="%(timestamp)s" user="%(user)s" uid="%(uid)s">\n' % obj)
        for nd in obj['nodes']:
            fd.write('<nd ref="%s" />\n' % (nd,))
        for k,v in obj['tags'].iteritems():
            fd.write('  <tag k="%s" v="%s"/>\n' % (k, v))
        fd.write('</way>\n')
    elif obj['type'] == 'R':
        fd.write('<relation id="%(id)d" version="%(version)s" changeset="%(changeset)s" timestamp="%(timestamp)s" user="%(user)s" uid="%(uid)s">\n' % obj)
        for mem in obj['members']:
            fd.write('  <member type="%s" ref="%s" role="%s"/>\n' % mem)
        for k,v in obj['tags'].iteritems():
            fd.write('  <tag k="%s" v="%s"/>\n' % (k, v))
        fd.write('</relation>\n')

@step(u'loading osm data')
def osm2pgsql_load_place(step):
    """Imports the previously defined OSM data into a fresh copy of a
       Nominatim test database.
    """

    world.osm2pgsql.sort(cmp=_sort_xml_entries)

    # create a OSM file in /tmp
    with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.osm', delete=False) as fd:
        fname = fd.name
        fd.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        fd.write('<osm version="0.6" generator="test-nominatim" timestamp="2014-08-26T20:22:02Z">\n')
        fd.write('\t<bounds minlat="43.72335" minlon="7.409205" maxlat="43.75169" maxlon="7.448637"/>\n')
        
        for obj in world.osm2pgsql:
            write_osm_obj(fd, obj)

        fd.write('</osm>\n')

    logger.debug( "Filename: %s" % fname)

    cmd = [os.path.join(world.config.source_dir, 'utils', 'setup.php')]
    cmd.extend(['--osm-file', fname, '--import-data','--osm2pgsql-cache', '300'])
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (outp, outerr) = proc.communicate()
    assert (proc.returncode == 0), "OSM data import failed:\n%s\n%s\n" % (outp, outerr)

    ### reintroduce the triggers/indexes we've lost by having osm2pgsql set up place again
    cur = world.conn.cursor()
    cur.execute("""CREATE TRIGGER place_before_delete BEFORE DELETE ON place
                    FOR EACH ROW EXECUTE PROCEDURE place_delete()""")
    cur.execute("""CREATE TRIGGER place_before_insert BEFORE INSERT ON place
                   FOR EACH ROW EXECUTE PROCEDURE place_insert()""")
    cur.execute("""CREATE UNIQUE INDEX idx_place_osm_unique on place using btree(osm_id,osm_type,class,type)""")
    world.conn.commit()

        
    os.remove(fname)
    world.osm2pgsql = []

actiontypes = { 'C' : 'create', 'M' : 'modify', 'D' : 'delete' }

@step(u'updating osm data')
def osm2pgsql_update_place(step):
    """Creates an osc file from the previously defined data and imports it
       into the database.
    """
    world.run_nominatim_script('setup', 'create-functions', 'create-partition-functions')
    cur = world.conn.cursor()
    cur.execute("""insert into placex (osm_type, osm_id, class, type, name, admin_level,
			       housenumber, street, addr_place, isin, postcode, country_code, extratags,
			       geometry) select * from place""")
    world.conn.commit()
    world.run_nominatim_script('setup', 'index', 'index-noanalyse')
    world.run_nominatim_script('setup', 'create-functions', 'create-partition-functions', 'enable-diff-updates')

    with tempfile.NamedTemporaryFile(dir='/tmp', delete=False) as fd:
        fname = fd.name
        fd.write("<?xml version='1.0' encoding='UTF-8'?>\n")
        fd.write('<osmChange version="0.6" generator="Osmosis 0.43.1">\n')

        for obj in world.osm2pgsql:
            fd.write('<%s>\n' % (actiontypes[obj['action']], ))
            write_osm_obj(fd, obj)
            fd.write('</%s>\n' % (actiontypes[obj['action']], ))

        fd.write('</osmChange>\n')

    logger.debug( "Filename: %s" % fname)

    cmd = [os.path.join(world.config.source_dir, 'utils', 'update.php')]
    cmd.extend(['--import-diff', fname])
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (outp, outerr) = proc.communicate()
    assert (proc.returncode == 0), "OSM data update failed:\n%s\n%s\n" % (outp, outerr)

    os.remove(fname)
    world.osm2pgsql = []
