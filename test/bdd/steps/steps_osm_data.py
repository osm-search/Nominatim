import tempfile
import random
import os

def write_opl_file(opl, grid):
    """ Create a temporary OSM file from OPL and return the file name. It is
        the responsibility of the caller to delete the file again.

        Node with missing coordinates, can retrieve their coordinates from
        a supplied grid. Failing that a random coordinate is assigned.
    """
    with tempfile.NamedTemporaryFile(suffix='.opl', delete=False) as fd:
        for line in opl.splitlines():
            if line.startswith('n') and line.find(' x') < 0:
                coord = grid.grid_node(int(line[1:].split(' ')[0]))
                if coord is None:
                    coord = (random.random() * 360 - 180,
                             random.random() * 180 - 90)
                line += " x%f y%f" % coord
            fd.write(line.encode('utf-8'))
            fd.write(b'\n')

        return fd.name

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
    # create an OSM file and import it
    fname = write_opl_file(context.text, context.osm)
    context.nominatim.run_setup_script('import-data', osm_file=fname,
                                       osm2pgsql_cache=300)
    os.remove(fname)

    ### reintroduce the triggers/indexes we've lost by having osm2pgsql set up place again
    cur = context.db.cursor()
    cur.execute("""CREATE TRIGGER place_before_delete BEFORE DELETE ON place
                    FOR EACH ROW EXECUTE PROCEDURE place_delete()""")
    cur.execute("""CREATE TRIGGER place_before_insert BEFORE INSERT ON place
                   FOR EACH ROW EXECUTE PROCEDURE place_insert()""")
    cur.execute("""CREATE UNIQUE INDEX idx_place_osm_unique on place using btree(osm_id,osm_type,class,type)""")
    context.db.commit()


@when(u'updating osm data')
def update_from_osm_file(context):
    """
    Update a database previously populated with 'loading osm data'.
    Needs to run indexing on the existing data first to yield the correct result.

    The data is expected as attached text in OPL format.
    """
    context.nominatim.copy_from_place(context.db)
    context.nominatim.run_setup_script('index', 'index-noanalyse')
    context.nominatim.run_setup_script('create-functions', 'create-partition-functions',
                                       'enable-diff-updates')

    # create an OSM file and import it
    fname = write_opl_file(context.text, context.osm)
    context.nominatim.run_update_script(import_diff=fname)
    os.remove(fname)
