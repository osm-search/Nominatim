import psycopg2.extras

from place_inserter import PlaceColumn
from table_compare import NominatimID, DBRow


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
    with context.db.cursor() as cur:
        cur.execute('ALTER TABLE place DISABLE TRIGGER place_before_insert')
        for row in context.table:
            PlaceColumn(context).add_row(row, named is not None).db_insert(cur)
        cur.execute('ALTER TABLE place ENABLE TRIGGER place_before_insert')

@given("the relations")
def add_data_to_planet_relations(context):
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

            tags = []
            for h in r.headings:
                if h.startswith("tags+"):
                    tags.extend((h[5:], r[h]))

            cur.execute("""INSERT INTO planet_osm_rels (id, way_off, rel_off, parts, members, tags)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (r['id'], last_node, last_way, parts, members, tags))

@given("the ways")
def add_data_to_planet_ways(context):
    with context.db.cursor() as cur:
        for r in context.table:
            tags = []
            for h in r.headings:
                if h.startswith("tags+"):
                    tags.extend((h[5:], r[h]))

            nodes = [ int(x.strip()) for x in r['nodes'].split(',') ]

            cur.execute("INSERT INTO planet_osm_ways (id, nodes, tags) VALUES (%s, %s, %s)",
                        (r['id'], nodes, tags))

################################ WHEN ##################################

@when("importing")
def import_and_index_data_from_place_table(context):
    """ Import data previously set up in the place table.
    """
    context.nominatim.copy_from_place(context.db)
    context.nominatim.run_setup_script('calculate-postcodes', 'index', 'index-noanalyse')
    check_database_integrity(context)

@when("updating places")
def update_place_table(context):
    context.nominatim.run_setup_script(
        'create-functions', 'create-partition-functions', 'enable-diff-updates')
    with context.db.cursor() as cur:
        for row in context.table:
            PlaceColumn(context).add_row(row, False).db_insert(cur)

    context.nominatim.reindex_placex(context.db)
    check_database_integrity(context)

@when("updating postcodes")
def update_postcodes(context):
    context.nominatim.run_update_script('calculate-postcodes')

@when("marking for delete (?P<oids>.*)")
def delete_places(context, oids):
    context.nominatim.run_setup_script(
        'create-functions', 'create-partition-functions', 'enable-diff-updates')
    with context.db.cursor() as cur:
        for oid in oids.split(','):
            NominatimID(oid).query_osm_id(cur, 'DELETE FROM place WHERE {}')

    context.nominatim.reindex_placex(context.db)

################################ THEN ##################################

@then("(?P<table>placex|place) contains(?P<exact> exactly)?")
def check_place_contents(context, table, exact):
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
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        NominatimID(oid).query_osm_id(cur, "SELECT * FROM %s where {}" % table)
        assert cur.rowcount == 0, \
               "Found {} entries for ID {}".format(cur.rowcount, oid)


@then("search_name contains(?P<exclude> not)?")
def check_search_name_contents(context, exclude):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for row in context.table:
            nid = NominatimID(row['object'])
            nid.row_by_place_id(cur, 'search_name',
                                ['ST_X(centroid) as cx', 'ST_Y(centroid) as cy'])
            assert cur.rowcount > 0, "No rows found for " + row['object']

            for res in cur:
                db_row = DBRow(nid, res, context)
                for h in row.headings:
                    if h in ('name_vector', 'nameaddress_vector'):
                        terms = [x.strip() for x in row[h].split(',') if not x.strip().startswith('#')]
                        words = [x.strip()[1:] for x in row[h].split(',') if x.strip().startswith('#')]
                        with context.db.cursor() as subcur:
                            subcur.execute(""" SELECT word_id, word_token
                                               FROM word, (SELECT unnest(%s::TEXT[]) as term) t
                                               WHERE word_token = make_standard_name(t.term)
                                                     and class is null and country_code is null
                                                     and operator is null
                                              UNION
                                               SELECT word_id, word_token
                                               FROM word, (SELECT unnest(%s::TEXT[]) as term) t
                                               WHERE word_token = ' ' || make_standard_name(t.term)
                                                     and class is null and country_code is null
                                                     and operator is null
                                           """,
                                           (terms, words))
                            if not exclude:
                                assert subcur.rowcount >= len(terms) + len(words), \
                                    "No word entry found for " + row[h] + ". Entries found: " + str(subcur.rowcount)
                            for wid in subcur:
                                if exclude:
                                    assert wid[0] not in res[h], "Found term for %s/%s: %s" % (row['object'], h, wid[1])
                                else:
                                    assert wid[0] in res[h], "Missing term for %s/%s: %s" % (row['object'], h, wid[1])
                    elif h != 'object':
                        assert db_row.contains(h, row[h]), db_row.assert_msg(h, row[h])

@then("location_postcode contains exactly")
def check_location_postcode(context):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT *, ST_AsText(geometry) as geomtxt FROM location_postcode")
        assert cur.rowcount == len(list(context.table)), \
            "Postcode table has %d rows, expected %d rows." % (cur.rowcount, len(list(context.table)))

        results = {}
        for row in cur:
            key = (row['country_code'], row['postcode'])
            assert key not in results, "Postcode table has duplicate entry: {}".format(row)
            results[key] = DBRow((row['country_code'],row['postcode']), row, context)

        for row in context.table:
            db_row = results.get((row['country'],row['postcode']))
            assert db_row is not None, \
                "Missing row for country '{}' postcode '{}'.".format(r['country'],['postcode'])

            db_row.assert_row(row, ('country', 'postcode'))

@then("word contains(?P<exclude> not)?")
def check_word_table(context, exclude):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for row in context.table:
            wheres = []
            values = []
            for h in row.headings:
                wheres.append("%s = %%s" % h)
                values.append(row[h])
            cur.execute("SELECT * from word WHERE %s" % ' AND '.join(wheres), values)
            if exclude:
                assert cur.rowcount == 0, "Row still in word table: %s" % '/'.join(values)
            else:
                assert cur.rowcount > 0, "Row not in word table: %s" % '/'.join(values)

@then("place_addressline contains")
def check_place_addressline(context):
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
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for row in context.table:
            pid = NominatimID(row['object']).get_place_id(cur)
            apid = NominatimID(row['address']).get_place_id(cur)
            cur.execute(""" SELECT * FROM place_addressline
                            WHERE place_id = %s AND address_place_id = %s""",
                        (pid, apid))
            assert cur.rowcount == 0, \
                "Row found for place %s and address %s" % (row['object'], row['address'])

@then("(?P<oid>\w+) expands to(?P<neg> no)? interpolation")
def check_location_property_osmline(context, oid, neg):
    nid = NominatimID(oid)

    assert 'W' == nid.typ, "interpolation must be a way"

    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("""SELECT *, ST_AsText(linegeo) as geomtxt
                       FROM location_property_osmline
                       WHERE osm_id = %s AND startnumber IS NOT NULL""",
                    (nid.oid, ))

        if neg:
            assert cur.rowcount == 0
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
                assert False, "Unexpected row %s" % (str(res))

            DBRow(nid, res, context).assert_row(row, ('start', 'end'))

        assert not todo


@then("search_name has no entry for (?P<oid>.*)")
def check_search_name_has_entry(context, oid):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        NominatimID(oid).row_by_place_id(cur, 'search_name')

        assert cur.rowcount == 0, \
               "Found {} entries for ID {}".format(cur.rowcount, oid)
