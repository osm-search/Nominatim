# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'import' subcommand.
"""
from typing import Optional
import argparse
import logging
from pathlib import Path

import psutil

from nominatim.config import Configuration
from nominatim.db.connection import connect, Connection
from nominatim.db import status, properties
from nominatim.tokenizer.base import AbstractTokenizer
from nominatim.version import version_str
from nominatim.clicmd.args import NominatimArgs
from nominatim.errors import UsageError

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=C0415

LOG = logging.getLogger()

class SetupAll:
    """\
    Create a new Nominatim database from an OSM file.

    This sub-command sets up a new Nominatim database from scratch starting
    with creating a new database in Postgresql. The user running this command
    needs superuser rights on the database.
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group_name = parser.add_argument_group('Required arguments')
        group1 = group_name.add_mutually_exclusive_group(required=True)
        group1.add_argument('--osm-file', metavar='FILE', action='append',
                           help='OSM file to be imported'
                                ' (repeat for importing multiple files)')
        group1.add_argument('--continue', dest='continue_at',
                           choices=['load-data', 'indexing', 'db-postprocess'],
                           help='Continue an import that was interrupted')
        group2 = parser.add_argument_group('Optional arguments')
        group2.add_argument('--osm2pgsql-cache', metavar='SIZE', type=int,
                           help='Size of cache to be used by osm2pgsql (in MB)')
        group2.add_argument('--reverse-only', action='store_true',
                           help='Do not create tables and indexes for searching')
        group2.add_argument('--no-partitions', action='store_true',
                           help=("Do not partition search indices "
                                 "(speeds up import of single country extracts)"))
        group2.add_argument('--no-updates', action='store_true',
                           help="Do not keep tables that are only needed for "
                                "updating the database later")
        group2.add_argument('--offline', action='store_true',
                           help="Do not attempt to load any additional data from the internet")
        group3 = parser.add_argument_group('Expert options')
        group3.add_argument('--ignore-errors', action='store_true',
                           help='Continue import even when errors in SQL are present')
        group3.add_argument('--index-noanalyse', action='store_true',
                           help='Do not perform analyse operations during index (expert only)')


    def run(self, args: NominatimArgs) -> int: # pylint: disable=too-many-statements
        from ..data import country_info
        from ..tools import database_import, refresh, postcodes, freeze
        from ..indexer.indexer import Indexer

        country_info.setup_country_config(args.config)

        if args.continue_at is None:
            files = args.get_osm_file_list()
            if not files:
                raise UsageError("No input files (use --osm-file).")

            LOG.warning('Creating database')
            database_import.setup_database_skeleton(args.config.get_libpq_dsn(),
                                                    rouser=args.config.DATABASE_WEBUSER)

            LOG.warning('Setting up country tables')
            country_info.setup_country_tables(args.config.get_libpq_dsn(),
                                              args.data_dir,
                                              args.no_partitions)

            LOG.warning('Importing OSM data file')
            database_import.import_osm_data(files,
                                            args.osm2pgsql_options(0, 1),
                                            drop=args.no_updates,
                                            ignore_errors=args.ignore_errors)

            self._setup_tables(args.config, args.reverse_only)

            LOG.warning('Importing wikipedia importance data')
            data_path = Path(args.config.WIKIPEDIA_DATA_PATH or args.project_dir)
            if refresh.import_wikipedia_articles(args.config.get_libpq_dsn(),
                                                 data_path) > 0:
                LOG.error('Wikipedia importance dump file not found. '
                          'Will be using default importances.')

        if args.continue_at is None or args.continue_at == 'load-data':
            LOG.warning('Initialise tables')
            with connect(args.config.get_libpq_dsn()) as conn:
                database_import.truncate_data_tables(conn)

            LOG.warning('Load data into placex table')
            database_import.load_data(args.config.get_libpq_dsn(),
                                      args.threads or psutil.cpu_count() or 1)

        LOG.warning("Setting up tokenizer")
        tokenizer = self._get_tokenizer(args.continue_at, args.config)

        if args.continue_at is None or args.continue_at == 'load-data':
            LOG.warning('Calculate postcodes')
            postcodes.update_postcodes(args.config.get_libpq_dsn(),
                                       args.project_dir, tokenizer)

        if args.continue_at is None or args.continue_at in ('load-data', 'indexing'):
            if args.continue_at is not None and args.continue_at != 'load-data':
                with connect(args.config.get_libpq_dsn()) as conn:
                    self._create_pending_index(conn, args.config.TABLESPACE_ADDRESS_INDEX)
            LOG.warning('Indexing places')
            indexer = Indexer(args.config.get_libpq_dsn(), tokenizer,
                              args.threads or psutil.cpu_count() or 1)
            indexer.index_full(analyse=not args.index_noanalyse)

        LOG.warning('Post-process tables')
        with connect(args.config.get_libpq_dsn()) as conn:
            database_import.create_search_indices(conn, args.config,
                                                  drop=args.no_updates)
            LOG.warning('Create search index for default country names.')
            country_info.create_country_names(conn, tokenizer,
                                              args.config.get_str_list('LANGUAGES'))
            if args.no_updates:
                freeze.drop_update_tables(conn)
        tokenizer.finalize_import(args.config)

        LOG.warning('Recompute word counts')
        tokenizer.update_statistics()

        webdir = args.project_dir / 'website'
        LOG.warning('Setup website at %s', webdir)
        with connect(args.config.get_libpq_dsn()) as conn:
            refresh.setup_website(webdir, args.config, conn)

        self._finalize_database(args.config.get_libpq_dsn(), args.offline)

        return 0


    def _setup_tables(self, config: Configuration, reverse_only: bool) -> None:
        """ Set up the basic database layout: tables, indexes and functions.
        """
        from ..tools import database_import, refresh

        with connect(config.get_libpq_dsn()) as conn:
            LOG.warning('Create functions (1st pass)')
            refresh.create_functions(conn, config, False, False)
            LOG.warning('Create tables')
            database_import.create_tables(conn, config, reverse_only=reverse_only)
            refresh.load_address_levels_from_config(conn, config)
            LOG.warning('Create functions (2nd pass)')
            refresh.create_functions(conn, config, False, False)
            LOG.warning('Create table triggers')
            database_import.create_table_triggers(conn, config)
            LOG.warning('Create partition tables')
            database_import.create_partition_tables(conn, config)
            LOG.warning('Create functions (3rd pass)')
            refresh.create_functions(conn, config, False, False)


    def _get_tokenizer(self, continue_at: Optional[str],
                       config: Configuration) -> AbstractTokenizer:
        """ Set up a new tokenizer or load an already initialised one.
        """
        from ..tokenizer import factory as tokenizer_factory

        if continue_at is None or continue_at == 'load-data':
            # (re)initialise the tokenizer data
            return tokenizer_factory.create_tokenizer(config)

        # just load the tokenizer
        return tokenizer_factory.get_tokenizer_for_db(config)


    def _create_pending_index(self, conn: Connection, tablespace: str) -> None:
        """ Add a supporting index for finding places still to be indexed.

            This index is normally created at the end of the import process
            for later updates. When indexing was partially done, then this
            index can greatly improve speed going through already indexed data.
        """
        if conn.index_exists('idx_placex_pendingsector'):
            return

        with conn.cursor() as cur:
            LOG.warning('Creating support index')
            if tablespace:
                tablespace = 'TABLESPACE ' + tablespace
            cur.execute(f"""CREATE INDEX idx_placex_pendingsector
                            ON placex USING BTREE (rank_address,geometry_sector)
                            {tablespace} WHERE indexed_status > 0
                         """)
        conn.commit()


    def _finalize_database(self, dsn: str, offline: bool) -> None:
        """ Determine the database date and set the status accordingly.
        """
        with connect(dsn) as conn:
            if not offline:
                try:
                    dbdate = status.compute_database_date(conn)
                    status.set_status(conn, dbdate)
                    LOG.info('Database is at %s.', dbdate)
                except Exception as exc: # pylint: disable=broad-except
                    LOG.error('Cannot determine date of database: %s', exc)

            properties.set_property(conn, 'database_version', version_str())
