"""
Implementation of the 'transition' subcommand.

This subcommand provides standins for functions that were available
through the PHP scripts but are now no longer directly accessible.
This module will be removed as soon as the transition phase is over.
"""
import logging

from ..db.connection import connect

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
        group = parser.add_argument_group('Options')
        group.add_argument('--no-partitions', action='store_true',
                           help='Do not partition search indices')

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
