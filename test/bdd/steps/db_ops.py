import base64
import random
import string
import re
from nose.tools import * # for assert functions
import psycopg2.extras

class PlaceColumn:

    def __init__(self, context, force_name):
        self.columns = { 'admin_level' : 100}
        self.force_name = force_name
        self.context = context
        self.geometry = None

    def add(self, key, value):
        if hasattr(self, 'set_key_' + key):
            getattr(self, 'set_key_' + key)(value)
        elif key.startswith('name+'):
            self.add_hstore('name', key[5:], value)
        elif key.startswith('extra+'):
            self.add_hstore('extratags', key[6:], value)
        else:
            assert_in(key, ('class', 'type', 'street', 'addr_place',
                            'isin', 'postcode'))
            self.columns[key] = None if value == '' else value

    def set_key_name(self, value):
        self.add_hstore('name', 'name', value)

    def set_key_osm(self, value):
        assert_in(value[0], 'NRW')
        ok_(value[1:].isdigit())

        self.columns['osm_type'] = value[0]
        self.columns['osm_id'] = int(value[1:])

    def set_key_admin(self, value):
        self.columns['admin_level'] = int(value)

    def set_key_housenr(self, value):
        self.columns['housenumber'] = None if value == '' else value

    def set_key_country(self, value):
        self.columns['country_code'] = None if value == '' else value

    def set_key_geometry(self, value):
        self.geometry = self.context.osm.parse_geometry(value, self.context.scene)
        assert_is_not_none(self.geometry)

    def add_hstore(self, column, key, value):
        if column in self.columns:
            self.columns[column][key] = value
        else:
            self.columns[column] = { key : value }

    def db_insert(self, cursor):
        assert_in('osm_type', self.columns)
        if self.force_name and 'name' not in self.columns:
            self.add_hstore('name', 'name', ''.join(random.choice(string.printable)
                                           for _ in range(int(random.random()*30))))

        if self.columns['osm_type'] == 'N' and self.geometry is None:
            pt = self.context.osm.grid_node(self.columns['osm_id'])
            if pt is None:
                pt = (random.random()*360 - 180, random.random()*180 - 90)

            self.geometry = "ST_SetSRID(ST_Point(%f, %f), 4326)" % pt
        else:
            assert_is_not_none(self.geometry, "Geometry missing")
        query = 'INSERT INTO place (%s, geometry) values(%s, %s)' % (
                     ','.join(self.columns.keys()),
                     ','.join(['%s' for x in range(len(self.columns))]),
                     self.geometry)
        cursor.execute(query, list(self.columns.values()))

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
            assert_is_not_none(m, "ID '%s' not of form <osmtype><osmid>[:<class>]" % oid)

            self.typ = m.group('tp')
            self.oid = m.group('id')
            self.cls = m.group('cls')

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
        eq_(1, cur.rowcount, "Expected exactly 1 entry in placex found %s" % cur.rowcount)

        return cur.fetchone()[0]


def assert_db_column(row, column, value, context):
    if column == 'object':
        return

    if column.startswith('centroid'):
        fac = float(column[9:]) if column.startswith('centroid*') else 1.0
        x, y = value.split(' ')
        assert_almost_equal(float(x) * fac, row['cx'], "Bad x coordinate")
        assert_almost_equal(float(y) * fac, row['cy'], "Bad y coordinate")
    elif column == 'geometry':
        geom = context.osm.parse_geometry(value, context.scene)
        cur = context.db.cursor()
        query = "SELECT ST_Equals(ST_SnapToGrid(%s, 0.00001, 0.00001), ST_SnapToGrid(ST_SetSRID('%s'::geometry, 4326), 0.00001, 0.00001))" % (
                 geom, row['geomtxt'],)
        cur.execute(query)
        eq_(cur.fetchone()[0], True, "(Row %s failed: %s)" % (column, query))
    elif value == '-':
        assert_is_none(row[column], "Row %s" % column)
    else:
        eq_(value, str(row[column]),
            "Row '%s': expected: %s, got: %s"
            % (column, value, str(row[column])))


################################ STEPS ##################################

@given(u'the scene (?P<scene>.+)')
def set_default_scene(context, scene):
    context.scene = scene

@given("the (?P<named>named )?places")
def add_data_to_place_table(context, named):
    cur = context.db.cursor()
    cur.execute('ALTER TABLE place DISABLE TRIGGER place_before_insert')
    for r in context.table:
        col = PlaceColumn(context, named is not None)

        for h in r.headings:
            col.add(h, r[h])

        col.db_insert(cur)
    cur.execute('ALTER TABLE place ENABLE TRIGGER place_before_insert')
    cur.close()
    context.db.commit()

@given("the relations")
def add_data_to_planet_relations(context):
    cur = context.db.cursor()
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
    context.db.commit()

@given("the ways")
def add_data_to_planet_ways(context):
    cur = context.db.cursor()
    for r in context.table:
        tags = []
        for h in r.headings:
            if h.startswith("tags+"):
                tags.extend((h[5:], r[h]))

        nodes = [ int(x.strip()) for x in r['nodes'].split(',') ]

        cur.execute("INSERT INTO planet_osm_ways (id, nodes, tags) VALUES (%s, %s, %s)",
                    (r['id'], nodes, tags))
    context.db.commit()

@when("importing")
def import_and_index_data_from_place_table(context):
    context.nominatim.run_setup_script('create-functions', 'create-partition-functions')
    cur = context.db.cursor()
    cur.execute(
        """insert into placex (osm_type, osm_id, class, type, name, admin_level,
           housenumber, street, addr_place, isin, postcode, country_code, extratags,
           geometry)
           select * from place where not (class='place' and type='houses' and osm_type='W')""")
    cur.execute(
            """insert into location_property_osmline
               (osm_id, interpolationtype, street, addr_place,
                postcode, calculated_country_code, linegeo)
             SELECT osm_id, housenumber, street, addr_place,
                    postcode, country_code, geometry from place
              WHERE class='place' and type='houses' and osm_type='W'
                    and ST_GeometryType(geometry) = 'ST_LineString'""")
    context.db.commit()
    context.nominatim.run_setup_script('index', 'index-noanalyse')

@when("updating places")
def update_place_table(context):
    context.nominatim.run_setup_script(
        'create-functions', 'create-partition-functions', 'enable-diff-updates')
    cur = context.db.cursor()
    for r in context.table:
        col = PlaceColumn(context, False)

        for h in r.headings:
            col.add(h, r[h])

        col.db_insert(cur)

    context.db.commit()

    while True:
        context.nominatim.run_update_script('index')

        cur = context.db.cursor()
        cur.execute("SELECT 'a' FROM placex WHERE indexed_status != 0 LIMIT 1")
        if cur.rowcount == 0:
            break

@when("marking for delete (?P<oids>.*)")
def delete_places(context, oids):
    context.nominatim.run_setup_script(
        'create-functions', 'create-partition-functions', 'enable-diff-updates')
    cur = context.db.cursor()
    for oid in oids.split(','):
        where, params = NominatimID(oid).table_select()
        cur.execute("DELETE FROM place WHERE " + where, params)
    context.db.commit()

    while True:
        context.nominatim.run_update_script('index')

        cur = context.db.cursor()
        cur.execute("SELECT 'a' FROM placex WHERE indexed_status != 0 LIMIT 1")
        if cur.rowcount == 0:
            break

@then("placex contains(?P<exact> exactly)?")
def check_placex_contents(context, exact):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    expected_content = set()
    for row in context.table:
        nid = NominatimID(row['object'])
        where, params = nid.table_select()
        cur.execute("""SELECT *, ST_AsText(geometry) as geomtxt,
                       ST_X(centroid) as cx, ST_Y(centroid) as cy
                       FROM placex where %s""" % where,
                    params)
        assert_less(0, cur.rowcount, "No rows found for " + row['object'])

        for res in cur:
            if exact:
                expected_content.add((res['osm_type'], res['osm_id'], res['class']))
            for h in row.headings:
                if h.startswith('name'):
                    name = h[5:] if h.startswith('name+') else 'name'
                    assert_in(name, res['name'])
                    eq_(res['name'][name], row[h])
                elif h.startswith('extratags+'):
                    eq_(res['extratags'][h[10:]], row[h])
                elif h in ('linked_place_id', 'parent_place_id'):
                    if row[h] == '0':
                        eq_(0, res[h])
                    elif row[h] == '-':
                        assert_is_none(res[h])
                    else:
                        eq_(NominatimID(row[h]).get_place_id(context.db.cursor()),
                            res[h])
                else:
                    assert_db_column(res, h, row[h], context)

    if exact:
        cur.execute('SELECT osm_type, osm_id, class from placex')
        eq_(expected_content, set([(r[0], r[1], r[2]) for r in cur]))

    context.db.commit()

@then("place contains(?P<exact> exactly)?")
def check_placex_contents(context, exact):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    expected_content = set()
    for row in context.table:
        nid = NominatimID(row['object'])
        where, params = nid.table_select()
        cur.execute("""SELECT *, ST_AsText(geometry) as geomtxt,
                       ST_GeometryType(geometry) as geometrytype
                       FROM place where %s""" % where,
                    params)
        assert_less(0, cur.rowcount, "No rows found for " + row['object'])

        for res in cur:
            if exact:
                expected_content.add((res['osm_type'], res['osm_id'], res['class']))
            for h in row.headings:
                msg = "%s: %s" % (row['object'], h)
                if h in ('name', 'extratags'):
                    if row[h] == '-':
                        assert_is_none(res[h], msg)
                    else:
                        vdict = eval('{' + row[h] + '}')
                        assert_equals(vdict, res[h], msg)
                elif h.startswith('name+'):
                    assert_equals(res['name'][h[5:]], row[h], msg)
                elif h.startswith('extratags+'):
                    assert_equals(res['extratags'][h[10:]], row[h], msg)
                elif h in ('linked_place_id', 'parent_place_id'):
                    if row[h] == '0':
                        assert_equals(0, res[h], msg)
                    elif row[h] == '-':
                        assert_is_none(res[h], msg)
                    else:
                        assert_equals(NominatimID(row[h]).get_place_id(context.db.cursor()),
                                      res[h], msg)
                else:
                    assert_db_column(res, h, row[h], context)

    if exact:
        cur.execute('SELECT osm_type, osm_id, class from place')
        eq_(expected_content, set([(r[0], r[1], r[2]) for r in cur]))

    context.db.commit()

@then("search_name contains")
def check_search_name_contents(context):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)

    for row in context.table:
        pid = NominatimID(row['object']).get_place_id(cur)
        cur.execute("""SELECT *, ST_X(centroid) as cx, ST_Y(centroid) as cy
                       FROM search_name WHERE place_id = %s""", (pid, ))
        assert_less(0, cur.rowcount, "No rows found for " + row['object'])

        for res in cur:
            for h in row.headings:
                if h in ('name_vector', 'nameaddress_vector'):
                    terms = [x.strip().replace('#', ' ') for x in row[h].split(',')]
                    subcur = context.db.cursor()
                    subcur.execute("""SELECT word_id, word_token
                                      FROM word, (SELECT unnest(%s) as term) t
                                      WHERE word_token = make_standard_name(t.term)""",
                                   (terms,))
                    ok_(subcur.rowcount >= len(terms))
                    for wid in subcur:
                        assert_in(wid[0], res[h],
                                  "Missing term for %s/%s: %s" % (pid, h, wid[1]))
                else:
                    assert_db_column(res, h, row[h], context)


    context.db.commit()

@then("(?P<oid>\w+) expands to(?P<neg> no)? interpolation")
def check_location_property_osmline(context, oid, neg):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    nid = NominatimID(oid)

    eq_('W', nid.typ, "interpolation must be a way")

    cur.execute("""SELECT *, ST_AsText(linegeo) as geomtxt
                   FROM location_property_osmline
                   WHERE osm_id = %s AND startnumber IS NOT NULL""",
                (nid.oid, ))

    if neg:
        eq_(0, cur.rowcount)
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
                if row[h] == '0':
                    eq_(0, res[h])
                elif row[h] == '-':
                    assert_is_none(res[h])
                else:
                    eq_(NominatimID(row[h]).get_place_id(context.db.cursor()),
                        res[h])
            else:
                assert_db_column(res, h, row[h], context)

    eq_(todo, [])


@then("(?P<table>placex|place) has no entry for (?P<oid>.*)")
def check_placex_has_entry(context, table, oid):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    nid = NominatimID(oid)
    where, params = nid.table_select()
    cur.execute("SELECT * FROM %s where %s" % (table, where), params)
    eq_(0, cur.rowcount)
    context.db.commit()

@then("search_name has no entry for (?P<oid>.*)")
def check_search_name_has_entry(context, oid):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    pid = NominatimID(oid).get_place_id(cur)
    cur.execute("SELECT * FROM search_name WHERE place_id = %s", (pid, ))
    eq_(0, cur.rowcount)
    context.db.commit()
