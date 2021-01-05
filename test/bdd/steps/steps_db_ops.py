import re
import psycopg2.extras

from check_functions import Almost
from place_inserter import PlaceColumn

class PlaceObjName(object):

    def __init__(self, placeid, conn):
        self.pid = placeid
        self.conn = conn

    def __str__(self):
        if self.pid is None:
            return "<null>"

        if self.pid == 0:
            return "place ID 0"

        cur = self.conn.cursor()
        cur.execute("""SELECT osm_type, osm_id, class
                       FROM placex WHERE place_id = %s""",
                    (self.pid, ))
        assert cur.rowcount == 1, "No entry found for place id %s" % self.pid

        return "%s%s:%s" % cur.fetchone()

def compare_place_id(expected, result, column, context):
    if expected == '0':
        assert result == 0, \
               "Bad place id in column {}. Expected: 0, got: {!s}.".format(
                    column, PlaceObjName(result, context.db))
    elif expected == '-':
        assert result is None, \
               "Bad place id in column {}: {!s}.".format(
                        column, PlaceObjName(result, context.db))
    else:
        assert NominatimID(expected).get_place_id(context.db.cursor()) == result, \
               "Bad place id in column {}. Expected: {}, got: {!s}.".format(
                    column, expected, PlaceObjName(result, context.db))

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


class NominatimID:
    """ Splits a unique identifier for places into its components.
        As place_ids cannot be used for testing, we use a unique
        identifier instead that is of the form <osmtype><osmid>[:<class>].
    """

    id_regex = re.compile(r"(?P<tp>[NRW])(?P<id>\d+)(:(?P<cls>\w+))?")

    def __init__(self, oid):
        self.typ = self.oid = self.cls = None

        if oid is not None:
            m = self.id_regex.fullmatch(oid)
            assert m is not None, "ID '%s' not of form <osmtype><osmid>[:<class>]" % oid

            self.typ = m.group('tp')
            self.oid = m.group('id')
            self.cls = m.group('cls')

    def __str__(self):
        if self.cls is None:
            return self.typ + self.oid

        return '%s%d:%s' % (self.typ, self.oid, self.cls)

    def table_select(self):
        """ Return where clause and parameter list to select the object
            from a Nominatim table.
        """
        where = 'osm_type = %s and osm_id = %s'
        params = [self.typ, self. oid]

        if self.cls is not None:
            where += ' and class = %s'
            params.append(self.cls)

        return where, params

    def get_place_id(self, cur):
        where, params = self.table_select()
        cur.execute("SELECT place_id FROM placex WHERE %s" % where, params)
        assert cur.rowcount == 1, \
            "Expected exactly 1 entry in placex for %s found %s" % (str(self), cur.rowcount)

        return cur.fetchone()[0]


def assert_db_column(row, column, value, context):
    if column == 'object':
        return

    if column.startswith('centroid'):
        if value == 'in geometry':
            query = """SELECT ST_Within(ST_SetSRID(ST_Point({}, {}), 4326),
                                        ST_SetSRID('{}'::geometry, 4326))""".format(
                      row['cx'], row['cy'], row['geomtxt'])
            cur = context.db.cursor()
            cur.execute(query)
            assert cur.fetchone()[0], "(Row %s failed: %s)" % (column, query)
        else:
            fac = float(column[9:]) if column.startswith('centroid*') else 1.0
            x, y = value.split(' ')
            assert Almost(float(x) * fac) == row['cx'], "Bad x coordinate"
            assert Almost(float(y) * fac) == row['cy'], "Bad y coordinate"
    elif column == 'geometry':
        geom = context.osm.parse_geometry(value, context.scene)
        cur = context.db.cursor()
        query = "SELECT ST_Equals(ST_SnapToGrid(%s, 0.00001, 0.00001), ST_SnapToGrid(ST_SetSRID('%s'::geometry, 4326), 0.00001, 0.00001))" % (
                 geom, row['geomtxt'],)
        cur.execute(query)
        assert cur.fetchone()[0], "(Row %s failed: %s)" % (column, query)
    elif value == '-':
        assert row[column] is None, "Row %s" % column
    else:
        assert value == str(row[column]), \
            "Row '%s': expected: %s, got: %s" % (column, value, str(row[column]))


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
            where, params = NominatimID(oid).table_select()
            cur.execute("DELETE FROM place WHERE " + where, params)

    context.nominatim.reindex_placex(context.db)

################################ THEN ##################################

@then("placex contains(?P<exact> exactly)?")
def check_placex_contents(context, exact):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        expected_content = set()
        for row in context.table:
            nid = NominatimID(row['object'])
            where, params = nid.table_select()
            cur.execute("""SELECT *, ST_AsText(geometry) as geomtxt,
                           ST_X(centroid) as cx, ST_Y(centroid) as cy
                           FROM placex where %s""" % where,
                        params)
            assert cur.rowcount > 0, "No rows found for " + row['object']

            for res in cur:
                if exact:
                    expected_content.add((res['osm_type'], res['osm_id'], res['class']))
                for h in row.headings:
                    if h in ('extratags', 'address'):
                        if row[h] == '-':
                            assert res[h] is None
                        else:
                            vdict = eval('{' + row[h] + '}')
                            assert vdict == res[h]
                    elif h.startswith('name'):
                        name = h[5:] if h.startswith('name+') else 'name'
                        assert name in res['name']
                        assert res['name'][name] == row[h]
                    elif h.startswith('extratags+'):
                        assert res['extratags'][h[10:]] == row[h]
                    elif h.startswith('addr+'):
                        if row[h] == '-':
                            if res['address'] is not None:
                                assert h[5:] not in res['address']
                        else:
                            assert h[5:] in res['address'], "column " + h
                            assert res['address'][h[5:]] == row[h], "column %s" % h
                    elif h in ('linked_place_id', 'parent_place_id'):
                        compare_place_id(row[h], res[h], h, context)
                    else:
                        assert_db_column(res, h, row[h], context)

        if exact:
            cur.execute('SELECT osm_type, osm_id, class from placex')
            assert expected_content == set([(r[0], r[1], r[2]) for r in cur])

@then("place contains(?P<exact> exactly)?")
def check_placex_contents(context, exact):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        expected_content = set()
        for row in context.table:
            nid = NominatimID(row['object'])
            where, params = nid.table_select()
            cur.execute("""SELECT *, ST_AsText(geometry) as geomtxt,
                           ST_GeometryType(geometry) as geometrytype
                           FROM place where %s""" % where,
                        params)
            assert cur.rowcount > 0, "No rows found for " + row['object']

            for res in cur:
                if exact:
                    expected_content.add((res['osm_type'], res['osm_id'], res['class']))
                for h in row.headings:
                    msg = "%s: %s" % (row['object'], h)
                    if h in ('name', 'extratags', 'address'):
                        if row[h] == '-':
                            assert res[h] is None, msg
                        else:
                            vdict = eval('{' + row[h] + '}')
                            assert vdict == res[h], msg
                    elif h.startswith('name+'):
                        assert res['name'][h[5:]] == row[h], msg
                    elif h.startswith('extratags+'):
                        assert res['extratags'][h[10:]] == row[h], msg
                    elif h.startswith('addr+'):
                        if row[h] == '-':
                            if res['address']  is not None:
                                assert h[5:] not in res['address']
                        else:
                            assert res['address'][h[5:]] == row[h], msg
                    elif h in ('linked_place_id', 'parent_place_id'):
                        compare_place_id(row[h], res[h], h, context)
                    else:
                        assert_db_column(res, h, row[h], context)

        if exact:
            cur.execute('SELECT osm_type, osm_id, class from place')
            assert expected_content, set([(r[0], r[1], r[2]) for r in cur])

@then("search_name contains(?P<exclude> not)?")
def check_search_name_contents(context, exclude):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        for row in context.table:
            pid = NominatimID(row['object']).get_place_id(cur)
            cur.execute("""SELECT *, ST_X(centroid) as cx, ST_Y(centroid) as cy
                           FROM search_name WHERE place_id = %s""", (pid, ))
            assert cur.rowcount > 0, "No rows found for " + row['object']

            for res in cur:
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
                                    assert wid[0] not in res[h], "Found term for %s/%s: %s" % (pid, h, wid[1])
                                else:
                                    assert wid[0] in res[h], "Missing term for %s/%s: %s" % (pid, h, wid[1])
                    else:
                        assert_db_column(res, h, row[h], context)

@then("location_postcode contains exactly")
def check_location_postcode(context):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        cur.execute("SELECT *, ST_AsText(geometry) as geomtxt FROM location_postcode")
        assert cur.rowcount == len(list(context.table)), \
            "Postcode table has %d rows, expected %d rows." % (cur.rowcount, len(list(context.table)))

        table = list(cur)
        for row in context.table:
            for i in range(len(table)):
                if table[i]['country_code'] != row['country'] \
                        or table[i]['postcode'] != row['postcode']:
                    continue
                for h in row.headings:
                    if h not in ('country', 'postcode'):
                        assert_db_column(table[i], h, row[h], context)

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
            pid = NominatimID(row['object']).get_place_id(cur)
            apid = NominatimID(row['address']).get_place_id(cur)
            cur.execute(""" SELECT * FROM place_addressline
                            WHERE place_id = %s AND address_place_id = %s""",
                        (pid, apid))
            assert cur.rowcount > 0, \
                        "No rows found for place %s and address %s" % (row['object'], row['address'])

            for res in cur:
                for h in row.headings:
                    if h not in ('address', 'object'):
                        assert_db_column(res, h, row[h], context)

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

            for h in row.headings:
                if h in ('start', 'end'):
                    continue
                elif h == 'parent_place_id':
                    compare_place_id(row[h], res[h], h, context)
                else:
                    assert_db_column(res, h, row[h], context)

        assert not todo


@then("(?P<table>placex|place) has no entry for (?P<oid>.*)")
def check_placex_has_entry(context, table, oid):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        nid = NominatimID(oid)
        where, params = nid.table_select()
        cur.execute("SELECT * FROM %s where %s" % (table, where), params)
        assert cur.rowcount == 0

@then("search_name has no entry for (?P<oid>.*)")
def check_search_name_has_entry(context, oid):
    with context.db.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
        pid = NominatimID(oid).get_place_id(cur)
        cur.execute("SELECT * FROM search_name WHERE place_id = %s", (pid, ))
        assert cur.rowcount == 0
