# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'admin' subcommand.
"""
import logging

from nominatim.tools.exec_utils import run_legacy_script

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

LOG = logging.getLogger()

class AdminFuncs:
    """\
    Analyse and maintain the database.
    """

    @staticmethod
    def add_args(parser):
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

    @staticmethod
    def run(args):
        if args.warm:
            return AdminFuncs._warm(args)

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

        return 1


    @staticmethod
    def _warm(args):
        LOG.warning('Warming database caches')
        params = ['warm.php']
        if args.target == 'reverse':
            params.append('--reverse-only')
        if args.target == 'search':
            params.append('--search-only')
        return run_legacy_script(*params, nominatim_env=args)
