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
            self.columns[key] = value

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
        self.columns['housenumber'] = value

    def set_key_country(self, value):
        self.columns['country_code'] = value

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
            self.geometry = "ST_SetSRID(ST_Point(%f, %f), 4326)" % (
                            random.random()*360 - 180, random.random()*180 - 90)

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

    id_regex = re.compile(r"(?P<tp>[NRW])(?P<id>\d+)(?P<cls>:\w+)?")

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
            where += ' class = %s'
            params.append(self.cls)

        return where, params

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
        """select insert_osmline (osm_id, housenumber, street, addr_place,
           postcode, country_code, geometry)
           from place where class='place' and type='houses' and osm_type='W'""")
    context.db.commit()
    context.nominatim.run_setup_script('index', 'index-noanalyse')


@then("placex contains(?P<exact> exactly)?")
def check_placex_contents(context, exact):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    if exact:
        cur.execute('SELECT osm_type, osm_id, class from placex')
        to_match = [(r[0], r[1], r[2]) for r in cur]

    for row in context.table:
        nid = NominatimID(row['object'])
        where, params = nid.table_select()
        cur.execute("""SELECT *, ST_AsText(geometry) as geomtxt,
                       ST_X(centroid) as cx, ST_Y(centroid) as cy
                       FROM placex where %s""" % where,
                    params)

        for res in cur:
            for h in row.headings:
                if h == 'object':
                    pass
                elif h.startswith('name'):
                    name = h[5:] if h.startswith('name+') else 'name'
                    assert_in(name, res['name'])
                    eq_(res['name'][name], row[h])
                elif h.startswith('extratags+'):
                    eq_(res['extratags'][h[10:]], row[h])
                elif h.startswith('centroid'):
                    fac = float(h[9:]) if h.startswith('centroid*') else 1.0
                    x, y = row[h].split(' ')
                    assert_almost_equal(float(x) * fac, res['cx'])
                    assert_almost_equal(float(y) * fac, res['cy'])
                else:
                    eq_(row[h], str(res[h]),
                        "Row '%s': expected: %s, got: %s" % (h, row[h], str(res[h])))
    context.db.commit()

@then("placex has no entry for (?P<oid>.*)")
def check_placex_has_entry(context, oid):
    cur = context.db.cursor(cursor_factory=psycopg2.extras.DictCursor)
    nid = NominatimID(oid)
    where, params = nid.table_select()
    cur.execute("""SELECT *, ST_AsText(geometry) as geomtxt,
                   ST_X(centroid) as cx, ST_Y(centroid) as cy
                   FROM placex where %s""" % where,
                params)
    eq_(0, cur.rowcount)
    context.db.commit()
