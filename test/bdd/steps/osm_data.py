import subprocess
import tempfile
import random
import os
from nose.tools import * # for assert functions

@given(u'the (\d+ )?grid')
def define_node_grid(context, grid_step):
    """
    Define a grid of node positions.
    """
    if grid_step is not None:
        grid_step = int(grd_step.strip())
    else:
        grid_step = 0.00001

    context.osm.clear_grid()

    i = 0
    for h in context.table.headings:
        if h.isdigit():
            context.osm.add_grid_node(int(h), 0, i)
        i += grid_step

    x = grid_step
    for r in context.table:
        y = 0
        for h in r:
            if h.isdigit():
                context.osm.add_grid_node(int(h), x, y)
            y += grid_step
        x += grid_step


@when(u'loading osm data')
def load_osm_file(context):
    """
    Load the given data into a freshly created test data using osm2pgsql.
    No further indexing is done.

    The data is expected as attached text in OPL format.
    """
    # create a OSM file in /tmp and import it
    with tempfile.NamedTemporaryFile(dir='/tmp', suffix='.opl', delete=False) as fd:
        fname = fd.name
        for line in context.text.splitlines():
            if line.startswith('n') and line.find(' x') < 0:
                coord = context.osm.grid_node(int(line[1:].split(' ')[0]))
                if coord is None:
                    coord = (random.random() * 360 - 180,
                             random.random() * 180 - 90)
                line += " x%f y%f" % coord
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
    """
    Update a database previously populated with 'loading osm data'.
    Needs to run indexing on the existing data first to yield the correct result.

    The data is expected as attached text in OPL format.
    """
    context.nominatim.run_setup_script('create-functions', 'create-partition-functions')

    cur = context.db.cursor()
    cur.execute("""insert into placex (osm_type, osm_id, class, type, name,
                   admin_level,  housenumber, street, addr_place, isin, postcode,
                   country_code, extratags, geometry) select * from place""")
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
