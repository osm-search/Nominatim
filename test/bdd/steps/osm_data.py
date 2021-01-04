import subprocess
import tempfile
import random
import os

@given(u'the ([0-9.]+ )?grid')
def define_node_grid(context, grid_step):
    """
    Define a grid of node positions.
    Use a table to define the grid. The nodes must be integer ids. Optionally
    you can give the grid distance. The default is 0.00001 degrees.
    """
    if grid_step is not None:
        grid_step = float(grid_step.strip())
    else:
        grid_step = 0.00001

    context.osm.set_grid([context.table.headings] + [list(h) for h in context.table],
                          grid_step)


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
    cur.execute("""insert into placex (osm_type, osm_id, class, type, name, admin_level, address, extratags, geometry)
                     select            osm_type, osm_id, class, type, name, admin_level, address, extratags, geometry from place""")
    cur.execute(
        """insert into location_property_osmline (osm_id, address, linegeo)
             SELECT osm_id, address, geometry from place
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
