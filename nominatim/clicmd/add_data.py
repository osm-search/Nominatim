"""
Implementation of the 'add-data' subcommand.
"""
import logging

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

LOG = logging.getLogger()

class UpdateAddData:
    """\
    Add additional data from a file or an online source.

    Data is only imported, not indexed. You need to call `nominatim index`
    to complete the process.
    """

    @staticmethod
    def add_args(parser):
        group_name = parser.add_argument_group('Source')
        group = group_name.add_mutually_exclusive_group(required=True)
        group.add_argument('--file', metavar='FILE',
                           help='Import data from an OSM file or diff file')
        group.add_argument('--diff', metavar='FILE',
                           help='Import data from an OSM diff file (deprecated: use --file)')
        group.add_argument('--node', metavar='ID', type=int,
                           help='Import a single node from the API')
        group.add_argument('--way', metavar='ID', type=int,
                           help='Import a single way from the API')
        group.add_argument('--relation', metavar='ID', type=int,
                           help='Import a single relation from the API')
        group.add_argument('--tiger-data', metavar='DIR',
                           help='Add housenumbers from the US TIGER census database.')
        group = parser.add_argument_group('Extra arguments')
        group.add_argument('--use-main-api', action='store_true',
                           help='Use OSM API instead of Overpass to download objects')
        group.add_argument('--osm2pgsql-cache', metavar='SIZE', type=int,
                           help='Size of cache to be used by osm2pgsql (in MB)')
        group.add_argument('--socket-timeout', dest='socket_timeout', type=int, default=60,
                           help='Set timeout for file downloads.')

    @staticmethod
    def run(args):
        from nominatim.tokenizer import factory as tokenizer_factory
        from nominatim.tools import tiger_data, add_osm_data

        if args.tiger_data:
            tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
            return tiger_data.add_tiger_data(args.tiger_data,
                                             args.config, args.threads or 1,
                                             tokenizer)

        osm2pgsql_params = args.osm2pgsql_options(default_cache=1000, default_threads=1)
        if args.file or args.diff:
            return add_osm_data.add_data_from_file(args.file or args.diff,
                                                   osm2pgsql_params)

        if args.node:
            return add_osm_data.add_osm_object('node', args.node,
                                               args.use_main_api,
                                               osm2pgsql_params)

        if args.way:
            return add_osm_data.add_osm_object('way', args.way,
                                               args.use_main_api,
                                               osm2pgsql_params)

        if args.relation:
            return add_osm_data.add_osm_object('relation', args.relation,
                                               args.use_main_api,
                                               osm2pgsql_params)

        return 0
