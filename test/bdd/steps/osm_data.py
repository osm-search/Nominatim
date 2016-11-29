import subprocess
import tempfile
import random
import os
from nose.tools import * # for assert functions

@when(u'loading osm data')
def load_osm_file(context):

    # create a OSM file in /tmp and import it
    with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.opl', delete=False) as fd:
        fname = fd.name
        for line in context.text.splitlines():
            if line.startswith('n') and line.find(' x') < 0:
                    line += " x%d y%d" % (random.random() * 360 - 180,
                                          random.random() * 180 - 90)
            fd.write(line.encode('utf-8'))
            fd.write(b'\n')

    context.nominatim.run_setup_script('import-data', osm_file=fname,
                                       osm2pgsql_cache=300)

    ### reintroduce the triggers/indexes we've lost by having osm2pgsql set up place again
    cur = context.db.cursor()
    cur.execute("""CREATE TRIGGER place_before_delete BEFORE DELETE ON place
                    FOR EACH ROW EXECUTE PROCEDURE place_delete()""")
    cur.execute("""CREATE TRIGGER place_before_insert BEFORE INSERT ON place
                   FOR EACH ROW EXECUTE PROCEDURE place_insert()""")
    cur.execute("""CREATE UNIQUE INDEX idx_place_osm_unique on place using btree(osm_id,osm_type,class,type)""")
    context.db.commit()

    os.remove(fname)

@when(u'updating osm data')
def update_from_osm_file(context):
    context.nominatim.run_setup_script('create-functions', 'create-partition-functions')

    cur = context.db.cursor()
    cur.execute("""insert into placex (osm_type, osm_id, class, type, name,
                   admin_level,  housenumber, street, addr_place, isin, postcode,
                   country_code, extratags, geometry) select * from place""")
    context.db.commit()
    context.nominatim.run_setup_script('index', 'index-noanalyse')
    context.nominatim.run_setup_script('create-functions', 'create-partition-functions',
                                       'enable-diff-updates')

    # create a OSM file in /tmp and import it
    with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.opl', delete=False) as fd:
        fname = fd.name
        for line in context.text.splitlines():
            if line.startswith('n') and line.find(' x') < 0:
                    line += " x%d y%d" % (random.random() * 360 - 180,
                                          random.random() * 180 - 90)
            fd.write(line.encode('utf-8'))
            fd.write(b'\n')

    context.nominatim.run_update_script(import_diff=fname)
    os.remove(fname)
