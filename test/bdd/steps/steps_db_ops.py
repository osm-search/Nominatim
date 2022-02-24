# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
import logging
from itertools import chain

import psycopg2.extras

from place_inserter import PlaceColumn
from table_compare import NominatimID, DBRow

from nominatim.indexer import indexer
from nominatim.tokenizer import factory as tokenizer_factory

def check_database_integrity(context):
    """ Check some generic constraints on the tables.
    """
    # place_addressline should not have duplicate (place_id, address_place_id)
    cur = context.db.cursor()
    cur.execute("""SELECT count(*) FROM
                    (SELECT place_id, address_place_id, count(*) as c
                     FROM place_addressline GROUP BY place_id, address_place_id) x
                   WHERE c > 1""")
    assert cur.fetchone()[0] == 0, "Duplicates found in place_addressline"


################################ GIVEN ##################################

@given("the (?P<named>named )?places")
def add_data_to_place_table(context, named):
    """ Add entries into the place table. 'named places' makes sure that
        the entries get a random name when none is explicitly given.
    """
    with context.db.cursor() as cur:
        cur.execute('ALTER TABLE place DISABLE TRIGGER place_before_insert')
        for row in context.table:
            PlaceColumn(context).add_row(row, named is not None).db_insert(cur)
        cur.execute('ALTER TABLE place ENABLE TRIGGER place_before_insert')

@given("the relations")
def add_data_to_planet_relations(context):
    """ Add entries into the osm2pgsql relation middle table. This is needed
        for tests on data that looks up members.
    """
    with context.db.cursor() as cur:
        for r in context.table:
            last_node = 0
            last_way = 0
            parts = []
            if r['members']:
                members = []
                for m in r['members'].split(','):
                    mid = NominatimID(m)
                    if mid.typ == 'N':
                        parts.insert(last_node, int(mid.oid))
                        last_node += 1
                        last_way += 1
                    elif mid.typ == 'W':
                        parts.insert(last_way, int(mid.oid))
                        last_way += 1
                    else:
                        parts.append(int(mid.oid))

                    members.extend((mid.typ.lower() + mid.oid, mid.cls or ''))
            else:
                members = None

            tags = chain.from_iterable([(h[5:], r[h]) for h in r.headings if h.startswith("tags+")])

            cur.execute("""INSERT INTO planet_osm_rels (id, way_off, rel_off, parts, members, tags)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (r['id'], last_node, last_way, parts, members, list(tags)))

@given("the ways")
def add_data_to_planet_ways(context):
    """ Add entries into the osm2pgsql way middle table. This is necessary for
        tests on that that looks up node ids in this table.
    """
    with context.db.cursor() as cur:
        for r in context.table:
            tags = chain.from_iterable([(h[5:], r[h]) for h in r.headings if h.startswith("tags+")])
            nodes = [ int(x.strip()) for x in r['nodes'].split(',') ]

            cur.execute("INSERT INTO planet_osm_ways (id, nodes, tags) VALUES (%s, %s, %s)",
                        (r['id'], nodes, list(tags)))

################################ WHEN ##################################

@when("importing")
def import_and_index_data_from_place_table(context):
    """ Import data previously set up in the place table.
    """
    context.nominatim.run_nominatim('import', '--continue', 'load-data',
                                              '--index-noanalyse', '-q')

    check_database_integrity(context)

@when("updating places")
def update_place_table(context):
    """ Update the place table with the given data. Also runs all triggers
        related to updates and reindexes the new data.
    """
    context.nominatim.run_nominatim('refresh', '--functions')
    with context.db.cursor() as cur:
        for row in context.table:
            PlaceColumn(context).add_row(row, False).db_insert(cur)

    context.nominatim.reindex_placex(context.db)
    check_database_integrity(context)

@when("updating postcodes")
def update_postcodes(context):
    """ Rerun the calculation of postcodes.
    """
    context.nominatim.run_nominatim('refresh', '--postcodes')

@when("marking for delete (?P<oids>.*)")
def delete_places(context, oids):
    """ Remove entries from the place table. Multiple ids may be given
        separated by commas. Also runs all triggers
        related to updates and reindexes the new data.
    """
    context.nominatim.run_nominatim('refresh', '--functions')
    with context.db.cursor() as cur:
        for oid in oids.split(','):
            NominatimID(oid).query_osm_id(cur, 'DELETE FROM place WHERE {}')

    context.nominatim.reindex_placex(context.db)

################################ THEN ##################################

@then("(?P<table>placex|place) contains(?P<exact> exactly)?")
def check_place_contents(context, table, exact):
    """ Check contents of place/placex tables. Each row represents a table row
        and all data must match. Data not present in the expected table, may
        be arbitry. The rows are identified via the 'object' column which must
        have an identifier of the form '<NRW><osm id>[:<class>]'. When multiple
        rows match (for example because 'class' was left out and there are
        multiple entries for the given OSM object) then all must match. All
        expected rows are expected to be present with at least one database row.
        When 'exactly' is given, there must not be additional rows in the database.
    """
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        expected_content = set()
        for row in context.table:
            nid = NominatimID(row['object'])
            query = 'SELECT *, ST_AsText(geometry) as geomtxt, ST_GeometryType(geometry) as geometrytype'
            if table == 'placex':
                query += ' ,ST_X(centroid) as cx, ST_Y(centroid) as cy'
            query += " FROM %s WHERE {}" % (table, )
            nid.query_osm_id(cur, query)
            assert cur.rowcount > 0, "No rows found for " + row['object']

            for res in cur:
                if exact:
                    expected_content.add((res['osm_type'], res['osm_id'], res['class']))

                DBRow(nid, res, context).assert_row(row, ['object'])

        if exact:
            cur.execute('SELECT osm_type, osm_id, class from {}'.format(table))
            assert expected_content == set([(r[0], r[1], r[2]) for r in cur])


@then("(?P<table>placex|place) has no entry for (?P<oid>.*)")
def check_place_has_entry(context, table, oid):
    """ Ensure that no database row for the given object exists. The ID
        must be of the form '<NRW><osm id>[:<class>]'.
    """
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        NominatimID(oid).query_osm_id(cur, "SELECT * FROM %s where {}" % table)
        assert cur.rowcount == 0, \
               "Found {} entries for ID {}".format(cur.rowcount, oid)


@then("search_name contains(?P<exclude> not)?")
def check_search_name_contents(context, exclude):
    """ Check contents of place/placex tables. Each row represents a table row
        and all data must match. Data not present in the expected table, may
        be arbitry. The rows are identified via the 'object' column which must
        have an identifier of the form '<NRW><osm id>[:<class>]'. All
        expected rows are expected to be present with at least one database row.
    """
    tokenizer = tokenizer_factory.get_tokenizer_for_db(context.nominatim.get_test_config())

    with tokenizer.name_analyzer() as analyzer:
        with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            for row in context.table:
                nid = NominatimID(row['object'])
                nid.row_by_place_id(cur, 'search_name',
                                    ['ST_X(centroid) as cx', 'ST_Y(centroid) as cy'])
                assert cur.rowcount > 0, "No rows found for " + row['object']

                for res in cur:
                    db_row = DBRow(nid, res, context)
                    for name, value in zip(row.headings, row.cells):
                        if name in ('name_vector', 'nameaddress_vector'):
                            items = [x.strip() for x in value.split(',')]
                            tokens = analyzer.get_word_token_info(items)

                            if not exclude:
                                assert len(tokens) >= len(items), \
                                       "No word entry found for {}. Entries found: {!s}".format(value, len(tokens))
                            for word, token, wid in tokens:
                                if exclude:
                                    assert wid not in res[name], \
                                           "Found term for {}/{}: {}".format(nid, name, wid)
                                else:
                                    assert wid in res[name], \
                                           "Missing term for {}/{}: {}".format(nid, name, wid)
                        elif name != 'object':
                            assert db_row.contains(name, value), db_row.assert_msg(name, value)

@then("search_name has no entry for (?P<oid>.*)")
def check_search_name_has_entry(context, oid):
    """ Check that there is noentry in the search_name table for the given
        objects. IDs are in format '<NRW><osm id>[:<class>]'.
    """
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        NominatimID(oid).row_by_place_id(cur, 'search_name')

        assert cur.rowcount == 0, \
               "Found {} entries for ID {}".format(cur.rowcount, oid)

@then("location_postcode contains exactly")
def check_location_postcode(context):
    """ Check full contents for location_postcode table. Each row represents a table row
        and all data must match. Data not present in the expected table, may
        be arbitry. The rows are identified via 'country' and 'postcode' columns.
        All rows must be present as excepted and there must not be additional
        rows.
    """
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT *, ST_AsText(geometry) as geomtxt FROM location_postcode")
        assert cur.rowcount == len(list(context.table)), \
            "Postcode table has {} rows, expected {}.".format(cur.rowcount, len(list(context.table)))

        results = {}
        for row in cur:
            key = (row['country_code'], row['postcode'])
            assert key not in results, "Postcode table has duplicate entry: {}".format(row)
            results[key] = DBRow((row['country_code'],row['postcode']), row, context)

        for row in context.table:
            db_row = results.get((row['country'],row['postcode']))
            assert db_row is not None, \
                f"Missing row for country '{row['country']}' postcode '{row['postcode']}'."

            db_row.assert_row(row, ('country', 'postcode'))

@then("there are(?P<exclude> no)? word tokens for postcodes (?P<postcodes>.*)")
def check_word_table_for_postcodes(context, exclude, postcodes):
    """ Check that the tokenizer produces postcode tokens for the given
        postcodes. The postcodes are a comma-separated list of postcodes.
        Whitespace matters.
    """
    nctx = context.nominatim
    tokenizer = tokenizer_factory.get_tokenizer_for_db(nctx.get_test_config())
    with tokenizer.name_analyzer() as ana:
        plist = [ana.normalize_postcode(p) for p in postcodes.split(',')]

    plist.sort()

    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        if nctx.tokenizer == 'icu':
            cur.execute("SELECT word FROM word WHERE type = 'P' and word = any(%s)",
                        (plist,))
        else:
            cur.execute("""SELECT word FROM word WHERE word = any(%s)
                             and class = 'place' and type = 'postcode'""",
                        (plist,))

        found = [row[0] for row in cur]
        assert len(found) == len(set(found)), f"Duplicate rows for postcodes: {found}"

    if exclude:
        assert len(found) == 0, f"Unexpected postcodes: {found}"
    else:
        assert set(found) == set(plist), \
        f"Missing postcodes {set(plist) - set(found)}. Found: {found}"

@then("place_addressline contains")
def check_place_addressline(context):
    """ Check the contents of the place_addressline table. Each row represents
        a table row and all data must match. Data not present in the expected
        table, may be arbitry. The rows are identified via the 'object' column,
        representing the addressee and the 'address' column, representing the
        address item.
    """
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for row in context.table:
            nid = NominatimID(row['object'])
            pid = nid.get_place_id(cur)
            apid = NominatimID(row['address']).get_place_id(cur)
            cur.execute(""" SELECT * FROM place_addressline
                            WHERE place_id = %s AND address_place_id = %s""",
                        (pid, apid))
            assert cur.rowcount > 0, \
                        "No rows found for place %s and address %s" % (row['object'], row['address'])

            for res in cur:
                DBRow(nid, res, context).assert_row(row, ('address', 'object'))

@then("place_addressline doesn't contain")
def check_place_addressline_exclude(context):
    """ Check that the place_addressline doesn't contain any entries for the
        given addressee/address item pairs.
    """
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for row in context.table:
            pid = NominatimID(row['object']).get_place_id(cur)
            apid = NominatimID(row['address']).get_place_id(cur, allow_empty=True)
            if apid is not None:
                cur.execute(""" SELECT * FROM place_addressline
                                WHERE place_id = %s AND address_place_id = %s""",
                            (pid, apid))
                assert cur.rowcount == 0, \
                    "Row found for place %s and address %s" % (row['object'], row['address'])

@then("W(?P<oid>\d+) expands to(?P<neg> no)? interpolation")
def check_location_property_osmline(context, oid, neg):
    """ Check that the given way is present in the interpolation table.
    """
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""SELECT *, ST_AsText(linegeo) as geomtxt
                       FROM location_property_osmline
                       WHERE osm_id = %s AND startnumber IS NOT NULL""",
                    (oid, ))

        if neg:
            assert cur.rowcount == 0, "Interpolation found for way {}.".format(oid)
            return

        todo = list(range(len(list(context.table))))
        for res in cur:
            for i in todo:
                row = context.table[i]
                if (int(row['start']) == res['startnumber']
                    and int(row['end']) == res['endnumber']):
                    todo.remove(i)
                    break
            else:
                assert False, "Unexpected row " + str(res)

            DBRow(oid, res, context).assert_row(row, ('start', 'end'))

        assert not todo


