"""
Implementation of the 'add-data' subcommand.
"""
import logging

from nominatim.tools.exec_utils import run_legacy_script

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
                           help='Import data from an OSM file')
        group.add_argument('--diff', metavar='FILE',
                           help='Import data from an OSM diff file')
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

    @staticmethod
    def run(args):
        from nominatim.tokenizer import factory as tokenizer_factory
        from nominatim.tools import tiger_data

        if args.tiger_data:
            tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
            return tiger_data.add_tiger_data(args.tiger_data,
                                             args.config, args.threads or 1,
                                             tokenizer)

        params = ['update.php']
        if args.file:
            params.extend(('--import-file', args.file))
        elif args.diff:
            params.extend(('--import-diff', args.diff))
        elif args.node:
            params.extend(('--import-node', args.node))
        elif args.way:
            params.extend(('--import-way', args.way))
        elif args.relation:
            params.extend(('--import-relation', args.relation))
        if args.use_main_api:
            params.append('--use-main-api')
        return run_legacy_script(*params, nominatim_env=args)
