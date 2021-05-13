"""
Implementation of 'refresh' subcommand.
"""
import logging
from pathlib import Path

from nominatim.db.connection import connect

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
        from ..tools import refresh, postcodes
        from ..tokenizer import factory as tokenizer_factory
        from ..indexer.indexer import Indexer

        tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)

        if args.postcodes:
            LOG.warning("Update postcodes centroid")
            postcodes.update_postcodes(args.config.get_libpq_dsn(),
                                       args.project_dir, tokenizer)
            indexer = Indexer(args.config.get_libpq_dsn(), tokenizer,
                              args.threads or 1)
            indexer.index_postcodes()

        if args.word_counts:
            LOG.warning('Recompute frequency of full-word search terms')
            refresh.recompute_word_counts(args.config.get_libpq_dsn(), args.sqllib_dir)

        if args.address_levels:
            cfg = Path(args.config.ADDRESS_LEVEL_CONFIG)
            LOG.warning('Updating address levels from %s', cfg)
            with connect(args.config.get_libpq_dsn()) as conn:
                refresh.load_address_levels_from_file(conn, cfg)

        if args.functions:
            LOG.warning('Create functions')
            with connect(args.config.get_libpq_dsn()) as conn:
                refresh.create_functions(conn, args.config,
                                         args.diffs, args.enable_debug_statements)
                tokenizer.update_sql_functions(args.config)

        if args.wiki_data:
            data_path = Path(args.config.WIKIPEDIA_DATA_PATH
                             or args.project_dir)
            LOG.warning('Import wikipdia article importance from %s', data_path)
            if refresh.import_wikipedia_articles(args.config.get_libpq_dsn(),
                                                 data_path) > 0:
                LOG.fatal('FATAL: Wikipedia importance dump file not found')
                return 1

        # Attention: importance MUST come after wiki data import.
        if args.importance:
            LOG.warning('Update importance values for database')
            with connect(args.config.get_libpq_dsn()) as conn:
                refresh.recompute_importance(conn)

        if args.website:
            webdir = args.project_dir / 'website'
            LOG.warning('Setting up website directory at %s', webdir)
            refresh.setup_website(webdir, args.config)

        return 0
