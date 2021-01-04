from pathlib import Path
import os

class GeometryFactory:
    """ Provides functions to create geometries from scenes and data grids.
    """

    def __init__(self):
        defpath = Path(__file__) / '..' / '..' / '..' / 'scenes' / 'data'
        self.scene_path = os.environ.get('SCENE_PATH', defpath.resolve())
        self.scene_cache = {}
        self.grid = {}

    def parse_geometry(self, geom, scene):
        """ Create a WKT SQL term for the given geometry.
            The function understands the following formats:

              [<scene>]:<name>
                 Geometry from a scene. If the scene is omitted, use the
                 default scene.
              <P>
                 Point geometry
              <P>,...,<P>
                 Line geometry
              (<P>,...,<P>)
                 Polygon geometry

           <P> may either be a coordinate of the form '<x> <y>' or a single
           number. In the latter case it must refer to a point in
           a previously defined grid.
        """
        if geom.find(':') >= 0:
            return "ST_SetSRID({}, 4326)".format(self.get_scene_geometry(scene, geom))

        if geom.find(',') < 0:
            out = "POINT({})".format(self.mk_wkt_point(geom))
        elif geom.find('(') < 0:
            out = "LINESTRING({})".format(self.mk_wkt_points(geom))
        else:
            out = "POLYGON(({}))".format(self.mk_wkt_points(geom.strip('() ')))

        return "ST_SetSRID('{}'::geometry, 4326)".format(out)

    def mk_wkt_point(self, point):
        """ Parse a point description.
            The point may either consist of 'x y' cooordinates or a number
            that refers to a grid setup.
        """
        geom = point.strip()
        if geom.find(' ') >= 0:
            return geom

        try:
            pt = self.grid_node(int(geom))
        except ValueError:
            assert False, "Scenario error: Point '{}' is not a number".format(geom)

        assert pt is not None, "Scenario error: Point '{}' not found in grid".format(geom)
        return "{} {}".format(*pt)

    def mk_wkt_points(self, geom):
        """ Parse a list of points.
            The list must be a comma-separated list of points. Points
            in coordinate and grid format may be mixed.
        """
        return ','.join([self.mk_wkt_point(x) for x in geom.split(',')])

    def get_scene_geometry(self, default_scene, name):
        """ Load the geometry from a scene.
        """
        geoms = []
        for obj in name.split('+'):
            oname = obj.strip()
            if oname.startswith(':'):
                assert default_scene is not None, "Scenario error: You need to set a scene"
                defscene = self.load_scene(default_scene)
                wkt = defscene[oname[1:]]
            else:
                scene, obj = oname.split(':', 2)
                scene_geoms = self.load_scene(scene)
                wkt = scene_geoms[obj]

            geoms.append("'{}'::geometry".format(wkt))

        if len(geoms) == 1:
            return geoms[0]

        return 'ST_LineMerge(ST_Collect(ARRAY[{}]))'.format(','.join(geoms))

    def load_scene(self, name):
        """ Load a scene from a file.
        """
        if name in self.scene_cache:
            return self.scene_cache[name]

        scene = {}
        with open(Path(self.scene_path) / "{}.wkt".format(name), 'r') as fd:
            for line in fd:
                if line.strip():
                    obj, wkt = line.split('|', 2)
                    scene[obj.strip()] = wkt.strip()
            self.scene_cache[name] = scene

        return scene

    def set_grid(self, lines, grid_step):
        """ Replace the grid with one from the given lines.
        """
        self.grid = {}
        y = 0
        for line in lines:
            x = 0
            for pt_id in line:
                if pt_id.isdigit():
                    self.grid[int(pt_id)] = (x, y)
                x += grid_step
            y += grid_step

    def grid_node(self, nodeid):
        """ Get the coordinates for the given grid node.
        """
        return self.grid.get(nodeid)
