"""
Implementation of the 'import' subcommand.
"""
import logging
from pathlib import Path

import psutil

from nominatim.tools.exec_utils import run_legacy_script
from nominatim.db.connection import connect
from nominatim.db import status, properties
from nominatim.version import NOMINATIM_VERSION
from nominatim.errors import UsageError

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

LOG = logging.getLogger()

class SetupAll:
    """\
    Create a new Nominatim database from an OSM file.
    """

    @staticmethod
    def add_args(parser):
        group_name = parser.add_argument_group('Required arguments')
        group = group_name.add_mutually_exclusive_group(required=True)
        group.add_argument('--osm-file', metavar='FILE',
                           help='OSM file to be imported.')
        group.add_argument('--continue', dest='continue_at',
                           choices=['load-data', 'indexing', 'db-postprocess'],
                           help='Continue an import that was interrupted')
        group = parser.add_argument_group('Optional arguments')
        group.add_argument('--osm2pgsql-cache', metavar='SIZE', type=int,
                           help='Size of cache to be used by osm2pgsql (in MB)')
        group.add_argument('--reverse-only', action='store_true',
                           help='Do not create tables and indexes for searching')
        group.add_argument('--no-partitions', action='store_true',
                           help=("Do not partition search indices "
                                 "(speeds up import of single country extracts)"))
        group.add_argument('--no-updates', action='store_true',
                           help="Do not keep tables that are only needed for "
                                "updating the database later")
        group = parser.add_argument_group('Expert options')
        group.add_argument('--ignore-errors', action='store_true',
                           help='Continue import even when errors in SQL are present')
        group.add_argument('--index-noanalyse', action='store_true',
                           help='Do not perform analyse operations during index')


    @staticmethod
    def run(args): # pylint: disable=too-many-statements
        from ..tools import database_import
        from ..tools import refresh
        from ..indexer.indexer import Indexer

        if args.osm_file and not Path(args.osm_file).is_file():
            LOG.fatal("OSM file '%s' does not exist.", args.osm_file)
            raise UsageError('Cannot access file.')

        if args.continue_at is None:
            database_import.setup_database_skeleton(args.config.get_libpq_dsn(),
                                                    args.data_dir,
                                                    args.no_partitions,
                                                    rouser=args.config.DATABASE_WEBUSER)

            LOG.warning('Installing database module')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.install_module(args.module_dir, args.project_dir,
                                               args.config.DATABASE_MODULE_PATH,
                                               conn=conn)

            LOG.warning('Importing OSM data file')
            database_import.import_osm_data(Path(args.osm_file),
                                            args.osm2pgsql_options(0, 1),
                                            drop=args.no_updates,
                                            ignore_errors=args.ignore_errors)

            with connect(args.config.get_libpq_dsn()) as conn:
                LOG.warning('Create functions (1st pass)')
                refresh.create_functions(conn, args.config, args.sqllib_dir,
                                         False, False)
                LOG.warning('Create tables')
                database_import.create_tables(conn, args.config, args.sqllib_dir,
                                              reverse_only=args.reverse_only)
                refresh.load_address_levels_from_file(conn, Path(args.config.ADDRESS_LEVEL_CONFIG))
                LOG.warning('Create functions (2nd pass)')
                refresh.create_functions(conn, args.config, args.sqllib_dir,
                                         False, False)
                LOG.warning('Create table triggers')
                database_import.create_table_triggers(conn, args.config, args.sqllib_dir)
                LOG.warning('Create partition tables')
                database_import.create_partition_tables(conn, args.config, args.sqllib_dir)
                LOG.warning('Create functions (3rd pass)')
                refresh.create_functions(conn, args.config, args.sqllib_dir,
                                         False, False)

            LOG.warning('Importing wikipedia importance data')
            data_path = Path(args.config.WIKIPEDIA_DATA_PATH or args.project_dir)
            if refresh.import_wikipedia_articles(args.config.get_libpq_dsn(),
                                                 data_path) > 0:
                LOG.error('Wikipedia importance dump file not found. '
                          'Will be using default importances.')

            LOG.warning('Initialise tables')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.truncate_data_tables(conn, args.config.MAX_WORD_FREQUENCY)

        if args.continue_at is None or args.continue_at == 'load-data':
            LOG.warning('Load data into placex table')
            database_import.load_data(args.config.get_libpq_dsn(),
                                      args.data_dir,
                                      args.threads or psutil.cpu_count() or 1)

            LOG.warning('Calculate postcodes')
            run_legacy_script('setup.php', '--calculate-postcodes',
                              nominatim_env=args, throw_on_fail=not args.ignore_errors)

        if args.continue_at is None or args.continue_at in ('load-data', 'indexing'):
            LOG.warning('Indexing places')
            indexer = Indexer(args.config.get_libpq_dsn(),
                              args.threads or psutil.cpu_count() or 1)
            indexer.index_full(analyse=not args.index_noanalyse)

        LOG.warning('Post-process tables')
        with connect(args.config.get_libpq_dsn()) as conn:
            database_import.create_search_indices(conn, args.config,
                                                  args.sqllib_dir,
                                                  drop=args.no_updates)
            LOG.warning('Create search index for default country names.')
            database_import.create_country_names(conn, args.config)

        webdir = args.project_dir / 'website'
        LOG.warning('Setup website at %s', webdir)
        refresh.setup_website(webdir, args.phplib_dir, args.config)

        with connect(args.config.get_libpq_dsn()) as conn:
            try:
                dbdate = status.compute_database_date(conn)
                status.set_status(conn, dbdate)
                LOG.info('Database is at %s.', dbdate)
            except Exception as exc: # pylint: disable=broad-except
                LOG.error('Cannot determine date of database: %s', exc)

            properties.set_property(conn, 'database_version',
                                    '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(NOMINATIM_VERSION))

        return 0
