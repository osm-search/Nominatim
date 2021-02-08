"""
Implementation of the 'admin' subcommand.
"""
from ..tools.exec_utils import run_legacy_script

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

class AdminFuncs:
    """\
    Analyse and maintain the database.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Admin task arguments')
        group.add_argument('--warm', action='store_true',
                           help='Warm database caches for search and reverse queries.')
        group.add_argument('--check-database', action='store_true',
                           help='Check that the database is complete and operational.')
        group = parser.add_argument_group('Arguments for cache warming')
        group.add_argument('--search-only', action='store_const', dest='target',
                           const='search',
                           help="Only pre-warm tables for search queries")
        group.add_argument('--reverse-only', action='store_const', dest='target',
                           const='reverse',
                           help="Only pre-warm tables for reverse queries")

    @staticmethod
    def run(args):
        if args.warm:
            AdminFuncs._warm(args)

        if args.check_database:
            run_legacy_script('check_import_finished.php', nominatim_env=args)

        return 0


    @staticmethod
    def _warm(args):
        params = ['warm.php']
        if args.target == 'reverse':
            params.append('--reverse-only')
        if args.target == 'search':
            params.append('--search-only')
        return run_legacy_script(*params, nominatim_env=args)
