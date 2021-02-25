"""
Implementation of the 'transition' subcommand.

This subcommand provides standins for functions that were available
through the PHP scripts but are now no longer directly accessible.
This module will be removed as soon as the transition phase is over.
"""
import logging
from pathlib import Path

from ..db.connection import connect
from ..errors import UsageError

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
        group.add_argument('--index', action='store_true',
                           help='Index the data')
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

    @staticmethod
    def run(args):
        from ..tools import database_import

        if args.create_db:
            LOG.warning('Create DB')
            database_import.create_db(args.config.get_libpq_dsn())

        if args.setup_db:
            LOG.warning('Setup DB')
            mpath = database_import.install_module(args.module_dir, args.project_dir,
                                                   args.config.DATABASE_MODULE_PATH)

            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.setup_extensions(conn)
                database_import.check_module_dir_path(conn, mpath)

            database_import.import_base_data(args.config.get_libpq_dsn(),
                                             args.data_dir, args.no_partitions)

        if args.import_data:
            LOG.warning('Import data')
            if not args.osm_file:
                raise UsageError('Missing required --osm-file argument')
            database_import.import_osm_data(Path(args.osm_file),
                                            args.osm2pgsql_options(0, 1),
                                            drop=args.drop)

        if args.index:
            LOG.warning('Indexing')
            from ..indexer.indexer import Indexer
            indexer = Indexer(args.config.get_libpq_dsn(), args.threads or 1)
            indexer.index_full()
