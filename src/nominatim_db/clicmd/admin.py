# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'admin' subcommand.
"""
import logging
import argparse
import random

import nominatim_api as napi
from nominatim_core.db.connection import connect
from .args import NominatimArgs

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

LOG = logging.getLogger()


class AdminFuncs:
    """\
    Analyse and maintain the database.
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Admin tasks')
        objs = group.add_mutually_exclusive_group(required=True)
        objs.add_argument('--warm', action='store_true',
                          help='Warm database caches for search and reverse queries')
        objs.add_argument('--check-database', action='store_true',
                          help='Check that the database is complete and operational')
        objs.add_argument('--migrate', action='store_true',
                          help='Migrate the database to a new software version')
        objs.add_argument('--analyse-indexing', action='store_true',
                          help='Print performance analysis of the indexing process')
        objs.add_argument('--collect-os-info', action="store_true",
                          help="Generate a report about the host system information")
        objs.add_argument('--clean-deleted', action='store', metavar='AGE',
                          help='Clean up deleted relations')
        group = parser.add_argument_group('Arguments for cache warming')
        group.add_argument('--search-only', action='store_const', dest='target',
                           const='search',
                           help="Only pre-warm tables for search queries")
        group.add_argument('--reverse-only', action='store_const', dest='target',
                           const='reverse',
                           help="Only pre-warm tables for reverse queries")
        group = parser.add_argument_group('Arguments for index anaysis')
        mgroup = group.add_mutually_exclusive_group()
        mgroup.add_argument('--osm-id', type=str,
                            help='Analyse indexing of the given OSM object')
        mgroup.add_argument('--place-id', type=int,
                            help='Analyse indexing of the given Nominatim object')


    def run(self, args: NominatimArgs) -> int:
        # pylint: disable=too-many-return-statements
        if args.warm:
            return self._warm(args)

        if args.check_database:
            LOG.warning('Checking database')
            from ..tools import check_database
            return check_database.check_database(args.config)

        if args.analyse_indexing:
            LOG.warning('Analysing performance of indexing function')
            from ..tools import admin
            admin.analyse_indexing(args.config, osm_id=args.osm_id, place_id=args.place_id)
            return 0

        if args.migrate:
            LOG.warning('Checking for necessary database migrations')
            from ..tools import migration
            return migration.migrate(args.config, args)

        if args.collect_os_info:
            LOG.warning("Reporting System Information")
            from ..tools import collect_os_info
            collect_os_info.report_system_information(args.config)
            return 0

        if args.clean_deleted:
            LOG.warning('Cleaning up deleted relations')
            from ..tools import admin
            admin.clean_deleted_relations(args.config, age=args.clean_deleted)
            return 0

        return 1


    def _warm(self, args: NominatimArgs) -> int:
        LOG.warning('Warming database caches')

        api = napi.NominatimAPI(args.project_dir)

        try:
            if args.target != 'search':
                for _ in range(1000):
                    api.reverse((random.uniform(-90, 90), random.uniform(-180, 180)),
                                address_details=True)

            if args.target != 'reverse':
                from ..tokenizer import factory as tokenizer_factory

                tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
                with connect(args.config.get_libpq_dsn()) as conn:
                    if conn.table_exists('search_name'):
                        words = tokenizer.most_frequent_words(conn, 1000)
                    else:
                        words = []

                for word in words:
                    api.search(word)
        finally:
            api.close()

        return 0
