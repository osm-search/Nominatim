import base64
import random
import string

def _format_placex_columns(row, force_name):
    out = {
        'osm_type' : row['osm'][0],
        'osm_id' : row['osm'][1:],
        'admin_level' : row.get('admin_level', 100)
    }

    for k in ('class', 'type', 'housenumber', 'street',
              'addr_place', 'isin', 'postcode', 'country_code'):
        if k in row.headings and row[k]:
            out[k] = row[k]

    if 'name' in row.headings:
        if row['name'].startswith("'"):
            out['name'] = eval('{' + row['name'] + '}')
        else:
            out['name'] = { 'name' : row['name'] }
    elif force_name:
        out['name'] = { 'name' : ''.join(random.choice(string.printable) for _ in range(int(random.random()*30))) }

    if 'extratags' in row.headings:
        out['extratags'] = eval('{%s}' % row['extratags'])

    return out


@given("the (?P<named>named )?places")
def add_data_to_place_table(context, named):
    cur = context.db.cursor()
    cur.execute('ALTER TABLE place DISABLE TRIGGER place_before_insert')
    for r in context.table:
        cols = _format_placex_columns(r, named is not None)

        if 'geometry' in r.headings:
            geometry = "'%s'::geometry" % context.osm.make_geometry(r['geometry'])
        elif cols['osm_type'] == 'N':
            geometry = "ST_Point(%f, %f)" % (random.random()*360 - 180, random.random()*180 - 90)
        else:
            raise RuntimeError("Missing geometry for place")

        query = 'INSERT INTO place (%s, geometry) values(%s, ST_SetSRID(%s, 4326))' % (
              ','.join(cols.keys()),
              ','.join(['%s' for x in range(len(cols))]),
              geometry
             )
        cur.execute(query, list(cols.values()))
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


@then("table (?P<table>\w+) contains(?P<exact> exactly)?")
def check_table_contents(context, table, exact):
    pass
