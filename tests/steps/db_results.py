""" Steps for checking the DB after import and update tests.

    There are two groups of test here. The first group tests
    the contents of db tables directly, the second checks
    query results by using the command line query tool.
"""

from nose.tools import *
from lettuce import *
import psycopg2
import psycopg2.extensions
import psycopg2.extras
import os
import random
import json
import re
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)

@step(u'table placex contains as names for (N|R|W)(\d+)')
def check_placex_names(step, osmtyp, osmid):
    """ Check for the exact content of the name hstore in placex.
    """
    cur = world.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute('SELECT name FROM placex where osm_type = %s and osm_id =%s', (osmtyp, int(osmid)))
    for line in cur:
        names = dict(line['name'])
        for name in step.hashes:
            assert_in(name['k'], names)
            assert_equals(names[name['k']], name['v'])
            del names[name['k']]
        assert_equals(len(names), 0)




@step(u'table ([a-z_]+) contains$')
def check_placex_content(step, tablename):
    """ check that the given lines are in the given table
        Entries are searched by osm_type/osm_id and then all
        given columns are tested. If there is more than one
        line for an OSM object, they must match in these columns.
    """
    try:
        cur = world.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        for line in step.hashes:
            osmtype, osmid, cls = world.split_id(line['object'])
            q = 'SELECT *'
            if tablename == 'placex':
                q = q + ", ST_X(centroid) as clat, ST_Y(centroid) as clon"
            if tablename == 'location_property_osmline':
                q = q + ' FROM %s where osm_id = %%s' % (tablename,)
            else:
                q = q + ' FROM %s where osm_type = %%s and osm_id = %%s' % (tablename,)
            if cls is None:
                if tablename == 'location_property_osmline':
                    params = (osmid,)
                else:
                    params = (osmtype, osmid)
            else:
                q = q + ' and class = %s'
                if tablename == 'location_property_osmline':
                    params = (osmid, cls)
                else:
                    params = (osmtype, osmid, cls)
            cur.execute(q, params)
            assert(cur.rowcount > 0)
            for res in cur:
                for k,v in line.iteritems():
                    if not k == 'object':
                        assert_in(k, res)
                        if type(res[k]) is dict:
                            val = world.make_hash(v)
                            assert_equals(res[k], val)
                        elif k in ('parent_place_id', 'linked_place_id'):
                            pid = world.get_placeid(v)
                            assert_equals(pid, res[k], "Results for '%s'/'%s' differ: '%s' != '%s'" % (line['object'], k, pid, res[k]))
                        elif k == 'centroid':
                            world.match_geometry((res['clat'], res['clon']), v)
                        else:
                            assert_equals(str(res[k]), v, "Results for '%s'/'%s' differ: '%s' != '%s'" % (line['object'], k, str(res[k]), v))
    finally:
        cur.close()
        world.conn.commit()

@step(u'table (placex?) has no entry for (N|R|W)(\d+)(:\w+)?')
def check_placex_missing(step, tablename, osmtyp, osmid, placeclass):
    cur = world.conn.cursor()
    try:
        q = 'SELECT count(*) FROM %s where osm_type = %%s and osm_id = %%s' % (tablename, )
        args = [osmtyp, int(osmid)]
        if placeclass is not None:
            q = q + ' and class = %s'
            args.append(placeclass[1:])
        cur.execute(q, args)
        numres = cur.fetchone()[0]
        assert_equals (numres, 0)
    finally:
        cur.close()
        world.conn.commit()

@step(u'table location_property_osmline has no entry for W(\d+)?')
def check_osmline_missing(step, osmid):
    cur = world.conn.cursor()
    try:
        q = 'SELECT count(*) FROM location_property_osmline where osm_id = %s' % (osmid, )
        cur.execute(q)
        numres = cur.fetchone()[0]
        assert_equals (numres, 0)
    finally:
        cur.close()
        world.conn.commit()

@step(u'search_name table contains$')
def check_search_name_content(step):
    cur = world.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    for line in step.hashes:
        placeid = world.get_placeid(line['place_id'])
        cur.execute('SELECT * FROM search_name WHERE place_id = %s', (placeid,))
        assert(cur.rowcount > 0)
        for res in cur:
            for k,v in line.iteritems():
                if k in ('search_rank', 'address_rank'):
                    assert_equals(int(v), res[k], "Results for '%s'/'%s' differ: '%s' != '%d'" % (line['place_id'], k, v, res[k]))
                elif k in ('importance'):
                    assert_equals(float(v), res[k], "Results for '%s'/'%s' differ: '%s' != '%d'" % (line['place_id'], k, v, res[k]))
                elif k in ('name_vector', 'nameaddress_vector'):
                    terms = [x.strip().replace('#', ' ') for x in v.split(',')]
                    cur.execute('SELECT word_id, word_token FROM word, (SELECT unnest(%s) as term) t WHERE word_token = make_standard_name(t.term)', (terms,))
                    assert cur.rowcount >= len(terms)
                    for wid in cur:
                        assert_in(wid['word_id'], res[k], "Missing term for %s/%s: %s" % (line['place_id'], k, wid['word_token']))
                elif k in ('country_code'):
                    assert_equals(v, res[k], "Results for '%s'/'%s' differ: '%s' != '%d'" % (line['place_id'], k, v, res[k]))
                elif k == 'place_id':
                    pass
                else:
                    raise Exception("Cannot handle field %s in search_name table" % (k, ))

@step(u'way (\d+) expands to lines')
def check_interpolation_lines(step, wayid):
    """Check that the correct interpolation line has been entered in
       location_property_osmline for the given source line/nodes.
       Expected are three columns:
       startnumber, endnumber and linegeo
    """
    lines = []
    for line in step.hashes:
        lines.append((line["startnumber"], line["endnumber"], line["geometry"]))
    cur = world.conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""SELECT startnumber::text, endnumber::text, st_astext(linegeo) as geometry
                   FROM location_property_osmline WHERE osm_id = %s""",
                   (int(wayid),))
    assert_equals(len(lines), cur.rowcount)
    for r in cur:
        linegeo = str(str(r["geometry"].split('(')[1]).split(')')[0]).replace(',', ', ')
        exp = (r["startnumber"], r["endnumber"], linegeo)
        assert_in(exp, lines)
        lines.remove(exp)

@step(u'way (\d+) expands exactly to housenumbers ([0-9,]*)')
def check_interpolated_housenumber_list(step, nodeid, numberlist):
    """ Checks that the interpolated house numbers corresponds
        to the given list.
    """
    expected = numberlist.split(',');
    cur = world.conn.cursor()
    cur.execute("""SELECT housenumber FROM placex
                   WHERE osm_type = 'W' and osm_id = %s
                   and class = 'place' and type = 'address'""", (int(nodeid),))
    for r in cur:
        assert_in(r[0], expected, "Unexpected house number %s for node %s." % (r[0], nodeid))
        expected.remove(r[0])
    assert_equals(0, len(expected), "Missing house numbers for way %s: %s" % (nodeid, expected))

@step(u'way (\d+) expands to no housenumbers')
def check_no_interpolated_housenumber_list(step, nodeid):
    """ Checks that the interpolated house numbers corresponds
        to the given list.
    """
    cur = world.conn.cursor()
    cur.execute("""SELECT housenumber FROM placex
                   WHERE osm_type = 'W' and osm_id = %s
                     and class = 'place' and type = 'address'""", (int(nodeid),))
    res = [r[0] for r in cur]
    assert_equals(0, len(res), "Unexpected house numbers for way %s: %s" % (nodeid, res))

@step(u'table search_name has no entry for (.*)')
def check_placex_missing(step, osmid):
    """ Checks if there is an entry in the search index for the
        given place object.
    """
    cur = world.conn.cursor()
    placeid = world.get_placeid(osmid)
    cur.execute('SELECT count(*) FROM search_name WHERE place_id =%s', (placeid,))
    numres = cur.fetchone()[0]
    assert_equals (numres, 0)

