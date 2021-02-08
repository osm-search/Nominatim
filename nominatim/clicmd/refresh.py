"""
Implementation of 'refresh' subcommand.
"""
import logging
from pathlib import Path

from ..db.connection import connect
from ..tools.exec_utils import run_legacy_script

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

LOG = logging.getLogger()

class UpdateRefresh:
    """\
    Recompute auxiliary data used by the indexing process.

    These functions must not be run in parallel with other update commands.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Data arguments')
        group.add_argument('--postcodes', action='store_true',
                           help='Update postcode centroid table')
        group.add_argument('--word-counts', action='store_true',
                           help='Compute frequency of full-word search terms')
        group.add_argument('--address-levels', action='store_true',
                           help='Reimport address level configuration')
        group.add_argument('--functions', action='store_true',
                           help='Update the PL/pgSQL functions in the database')
        group.add_argument('--wiki-data', action='store_true',
                           help='Update Wikipedia/data importance numbers.')
        group.add_argument('--importance', action='store_true',
                           help='Recompute place importances (expensive!)')
        group.add_argument('--website', action='store_true',
                           help='Refresh the directory that serves the scripts for the web API')
        group = parser.add_argument_group('Arguments for function refresh')
        group.add_argument('--no-diff-updates', action='store_false', dest='diffs',
                           help='Do not enable code for propagating updates')
        group.add_argument('--enable-debug-statements', action='store_true',
                           help='Enable debug warning statements in functions')

    @staticmethod
    def run(args):
        from ..tools import refresh

        if args.postcodes:
            LOG.warning("Update postcodes centroid")
            conn = connect(args.config.get_libpq_dsn())
            refresh.update_postcodes(conn, args.data_dir)
            conn.close()

        if args.word_counts:
            LOG.warning('Recompute frequency of full-word search terms')
            conn = connect(args.config.get_libpq_dsn())
            refresh.recompute_word_counts(conn, args.data_dir)
            conn.close()

        if args.address_levels:
            cfg = Path(args.config.ADDRESS_LEVEL_CONFIG)
            LOG.warning('Updating address levels from %s', cfg)
            conn = connect(args.config.get_libpq_dsn())
            refresh.load_address_levels_from_file(conn, cfg)
            conn.close()

        if args.functions:
            LOG.warning('Create functions')
            conn = connect(args.config.get_libpq_dsn())
            refresh.create_functions(conn, args.config, args.data_dir,
                                     args.diffs, args.enable_debug_statements)
            conn.close()

        if args.wiki_data:
            run_legacy_script('setup.php', '--import-wikipedia-articles',
                              nominatim_env=args, throw_on_fail=True)
        # Attention: importance MUST come after wiki data import.
        if args.importance:
            run_legacy_script('update.php', '--recompute-importance',
                              nominatim_env=args, throw_on_fail=True)
        if args.website:
            run_legacy_script('setup.php', '--setup-website',
                              nominatim_env=args, throw_on_fail=True)

        return 0
