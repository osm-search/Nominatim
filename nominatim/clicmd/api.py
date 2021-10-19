"""
Subcommand definitions for API calls from the command line.
"""
import logging

from nominatim.tools.exec_utils import run_api_script

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111

LOG = logging.getLogger()

STRUCTURED_QUERY = (
    ('street', 'housenumber and street'),
    ('city', 'city, town or village'),
    ('county', 'county'),
    ('state', 'state'),
    ('country', 'country'),
    ('postalcode', 'postcode')
)

EXTRADATA_PARAMS = (
    ('addressdetails', 'Include a breakdown of the address into elements'),
    ('extratags', ("Include additional information if available "
                   "(e.g. wikipedia link, opening hours)")),
    ('namedetails', 'Include a list of alternative names')
)

DETAILS_SWITCHES = (
    ('addressdetails', 'Include a breakdown of the address into elements'),
    ('keywords', 'Include a list of name keywords and address keywords'),
    ('linkedplaces', 'Include a details of places that are linked with this one'),
    ('hierarchy', 'Include details of places lower in the address hierarchy'),
    ('group_hierarchy', 'Group the places by type'),
    ('polygon_geojson', 'Include geometry of result')
)

def _add_api_output_arguments(parser):
    group = parser.add_argument_group('Output arguments')
    group.add_argument('--format', default='jsonv2',
                       choices=['xml', 'json', 'jsonv2', 'geojson', 'geocodejson'],
                       help='Format of result')
    for name, desc in EXTRADATA_PARAMS:
        group.add_argument('--' + name, action='store_true', help=desc)

    group.add_argument('--lang', '--accept-language', metavar='LANGS',
                       help='Preferred language order for presenting search results')
    group.add_argument('--polygon-output',
                       choices=['geojson', 'kml', 'svg', 'text'],
                       help='Output geometry of results as a GeoJSON, KML, SVG or WKT')
    group.add_argument('--polygon-threshold', type=float, metavar='TOLERANCE',
                       help=("Simplify output geometry."
                             "Parameter is difference tolerance in degrees."))


class APISearch:
    """\
    Execute a search query.

    This command works exactly the same as if calling the /search endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Search/
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Query arguments')
        group.add_argument('--query',
                           help='Free-form query string')
        for name, desc in STRUCTURED_QUERY:
            group.add_argument('--' + name, help='Structured query: ' + desc)

        _add_api_output_arguments(parser)

        group = parser.add_argument_group('Result limitation')
        group.add_argument('--countrycodes', metavar='CC,..',
                           help='Limit search results to one or more countries')
        group.add_argument('--exclude_place_ids', metavar='ID,..',
                           help='List of search object to be excluded')
        group.add_argument('--limit', type=int,
                           help='Limit the number of returned results')
        group.add_argument('--viewbox', metavar='X1,Y1,X2,Y2',
                           help='Preferred area to find search results')
        group.add_argument('--bounded', action='store_true',
                           help='Strictly restrict results to viewbox area')

        group = parser.add_argument_group('Other arguments')
        group.add_argument('--no-dedupe', action='store_false', dest='dedupe',
                           help='Do not remove duplicates from the result list')


    @staticmethod
    def run(args):
        if args.query:
            params = dict(q=args.query)
        else:
            params = {k: getattr(args, k) for k, _ in STRUCTURED_QUERY if getattr(args, k)}

        for param, _ in EXTRADATA_PARAMS:
            if getattr(args, param):
                params[param] = '1'
        for param in ('format', 'countrycodes', 'exclude_place_ids', 'limit', 'viewbox'):
            if getattr(args, param):
                params[param] = getattr(args, param)
        if args.lang:
            params['accept-language'] = args.lang
        if args.polygon_output:
            params['polygon_' + args.polygon_output] = '1'
        if args.polygon_threshold:
            params['polygon_threshold'] = args.polygon_threshold
        if args.bounded:
            params['bounded'] = '1'
        if not args.dedupe:
            params['dedupe'] = '0'

        return run_api_script('search', args.project_dir,
                              phpcgi_bin=args.phpcgi_path, params=params)

class APIReverse:
    """\
    Execute API reverse query.

    This command works exactly the same as if calling the /reverse endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Reverse/
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Query arguments')
        group.add_argument('--lat', type=float, required=True,
                           help='Latitude of coordinate to look up (in WGS84)')
        group.add_argument('--lon', type=float, required=True,
                           help='Longitude of coordinate to look up (in WGS84)')
        group.add_argument('--zoom', type=int,
                           help='Level of detail required for the address')

        _add_api_output_arguments(parser)


    @staticmethod
    def run(args):
        params = dict(lat=args.lat, lon=args.lon)
        if args.zoom is not None:
            params['zoom'] = args.zoom

        for param, _ in EXTRADATA_PARAMS:
            if getattr(args, param):
                params[param] = '1'
        if args.format:
            params['format'] = args.format
        if args.lang:
            params['accept-language'] = args.lang
        if args.polygon_output:
            params['polygon_' + args.polygon_output] = '1'
        if args.polygon_threshold:
            params['polygon_threshold'] = args.polygon_threshold

        return run_api_script('reverse', args.project_dir,
                              phpcgi_bin=args.phpcgi_path, params=params)


class APILookup:
    """\
    Execute API lookup query.

    This command works exactly the same as if calling the /lookup endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Lookup/
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Query arguments')
        group.add_argument('--id', metavar='OSMID',
                           action='append', required=True, dest='ids',
                           help='OSM id to lookup in format <NRW><id> (may be repeated)')

        _add_api_output_arguments(parser)


    @staticmethod
    def run(args):
        params = dict(osm_ids=','.join(args.ids))

        for param, _ in EXTRADATA_PARAMS:
            if getattr(args, param):
                params[param] = '1'
        if args.format:
            params['format'] = args.format
        if args.lang:
            params['accept-language'] = args.lang
        if args.polygon_output:
            params['polygon_' + args.polygon_output] = '1'
        if args.polygon_threshold:
            params['polygon_threshold'] = args.polygon_threshold

        return run_api_script('lookup', args.project_dir,
                              phpcgi_bin=args.phpcgi_path, params=params)


class APIDetails:
    """\
    Execute API details query.

    This command works exactly the same as if calling the /details endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Details/
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Query arguments')
        objs = group.add_mutually_exclusive_group(required=True)
        objs.add_argument('--node', '-n', type=int,
                          help="Look up the OSM node with the given ID.")
        objs.add_argument('--way', '-w', type=int,
                          help="Look up the OSM way with the given ID.")
        objs.add_argument('--relation', '-r', type=int,
                          help="Look up the OSM relation with the given ID.")
        objs.add_argument('--place_id', '-p', type=int,
                          help='Database internal identifier of the OSM object to look up')
        group.add_argument('--class', dest='object_class',
                           help=("Class type to disambiguated multiple entries "
                                 "of the same object."))

        group = parser.add_argument_group('Output arguments')
        for name, desc in DETAILS_SWITCHES:
            group.add_argument('--' + name, action='store_true', help=desc)
        group.add_argument('--lang', '--accept-language', metavar='LANGS',
                           help='Preferred language order for presenting search results')

    @staticmethod
    def run(args):
        if args.node:
            params = dict(osmtype='N', osmid=args.node)
        elif args.way:
            params = dict(osmtype='W', osmid=args.node)
        elif args.relation:
            params = dict(osmtype='R', osmid=args.node)
        else:
            params = dict(place_id=args.place_id)
        if args.object_class:
            params['class'] = args.object_class
        for name, _ in DETAILS_SWITCHES:
            params[name] = '1' if getattr(args, name) else '0'

        return run_api_script('details', args.project_dir,
                              phpcgi_bin=args.phpcgi_path, params=params)


class APIStatus:
    """\
    Execute API status query.

    This command works exactly the same as if calling the /status endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Status/
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('API parameters')
        group.add_argument('--format', default='text', choices=['text', 'json'],
                           help='Format of result')

    @staticmethod
    def run(args):
        return run_api_script('status', args.project_dir,
                              phpcgi_bin=args.phpcgi_path,
                              params=dict(format=args.format))
