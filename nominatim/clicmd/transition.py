"""
Implementation of the 'transition' subcommand.

This subcommand provides standins for functions that were available
through the PHP scripts but are now no longer directly accessible.
This module will be removed as soon as the transition phase is over.
"""
import logging
from pathlib import Path

from nominatim.db.connection import connect
from nominatim.db import status
from nominatim.errors import UsageError

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

LOG = logging.getLogger()

class AdminTransition:
    """\
    Internal functions for code transition. Do not use.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Sub-functions')
        group.add_argument('--create-db', action='store_true',
                           help='Create nominatim db')
        group.add_argument('--setup-db', action='store_true',
                           help='Build a blank nominatim db')
        group.add_argument('--import-data', action='store_true',
                           help='Import a osm file')
        group.add_argument('--load-data', action='store_true',
                           help='Copy data to live tables from import table')
        group.add_argument('--create-tables', action='store_true',
                           help='Create main tables')
        group.add_argument('--create-partition-tables', action='store_true',
                           help='Create required partition tables')
        group.add_argument('--index', action='store_true',
                           help='Index the data')
        group.add_argument('--create-search-indices', action='store_true',
                           help='Create additional indices required for search and update')
        group.add_argument('--create-country-names', action='store_true',
                           help='Create search index for default country names.')
        group = parser.add_argument_group('Options')
        group.add_argument('--no-partitions', action='store_true',
                           help='Do not partition search indices')
        group.add_argument('--osm-file', metavar='FILE',
                           help='File to import')
        group.add_argument('--drop', action='store_true',
                           help='Drop tables needed for updates, making the database readonly')
        group.add_argument('--osm2pgsql-cache', metavar='SIZE', type=int,
                           help='Size of cache to be used by osm2pgsql (in MB)')
        group.add_argument('--no-analyse', action='store_true',
                           help='Do not perform analyse operations during index')
        group.add_argument('--ignore-errors', action='store_true',
                           help="Ignore certain erros on import.")
        group.add_argument('--reverse-only', action='store_true',
                           help='Do not create search tables and indexes')
        group.add_argument('--tiger-data', metavar='FILE',
                           help='File to import')

    @staticmethod
    def run(args): # pylint: disable=too-many-statements
        from ..tools import database_import, tiger_data
        from ..tools import refresh

        if args.create_db:
            LOG.warning('Create DB')
            database_import.create_db(args.config.get_libpq_dsn())

        if args.setup_db:
            LOG.warning('Setup DB')

            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.setup_extensions(conn)
                database_import.install_module(args.module_dir, args.project_dir,
                                               args.config.DATABASE_MODULE_PATH,
                                               conn=conn)

            database_import.import_base_data(args.config.get_libpq_dsn(),
                                             args.data_dir, args.no_partitions)

        if args.import_data:
            LOG.warning('Import data')
            if not args.osm_file:
                raise UsageError('Missing required --osm-file argument')
            database_import.import_osm_data(Path(args.osm_file),
                                            args.osm2pgsql_options(0, 1),
                                            drop=args.drop,
                                            ignore_errors=args.ignore_errors)

        if args.create_tables:
            LOG.warning('Create Tables')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.create_tables(conn, args.config, args.sqllib_dir, args.reverse_only)
                refresh.load_address_levels_from_file(conn, Path(args.config.ADDRESS_LEVEL_CONFIG))
                refresh.create_functions(conn, args.config, args.sqllib_dir,
                                         enable_diff_updates=False)
                database_import.create_table_triggers(conn, args.config, args.sqllib_dir)

        if args.create_partition_tables:
            LOG.warning('Create Partition Tables')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.create_partition_tables(conn, args.config, args.sqllib_dir)

        if args.load_data:
            LOG.warning('Load data')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.truncate_data_tables(conn, args.config.MAX_WORD_FREQUENCY)
            database_import.load_data(args.config.get_libpq_dsn(),
                                      args.data_dir,
                                      args.threads or 1)

            with connect(args.config.get_libpq_dsn()) as conn:
                try:
                    status.set_status(conn, status.compute_database_date(conn))
                except Exception as exc: # pylint: disable=broad-except
                    LOG.error('Cannot determine date of database: %s', exc)

        if args.index:
            LOG.warning('Indexing')
            from ..indexer.indexer import Indexer
            indexer = Indexer(args.config.get_libpq_dsn(), args.threads or 1)
            indexer.index_full()

        if args.create_search_indices:
            LOG.warning('Create Search indices')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.create_search_indices(conn, args.config, args.sqllib_dir, args.drop)

        if args.tiger_data:
            LOG.warning('Tiger data')
            tiger_data.add_tiger_data(args.config.get_libpq_dsn(),
                                      args.tiger_data,
                                      args.threads or 1,
                                      args.config,
                                      args.sqllib_dir)

        if args.create_country_names:
            LOG.warning('Create search index for default country names.')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.create_country_names(conn, args.config)
