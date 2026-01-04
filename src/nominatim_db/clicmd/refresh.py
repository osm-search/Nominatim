# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of 'refresh' subcommand.
"""
from typing import Tuple, Optional
import argparse
import logging
from pathlib import Path
import asyncio

from ..config import Configuration
from ..db.connection import connect, table_exists
from ..tokenizer.base import AbstractTokenizer
from .args import NominatimArgs
from ..tools.admin import grant_readonly_access



LOG = logging.getLogger()


def _parse_osm_object(obj: str) -> Tuple[str, int]:
    """ Parse the given argument into a tuple of OSM type and ID.
        Raises an ArgumentError if the format is not recognized.
    """
    if len(obj) < 2 or obj[0].lower() not in 'nrw' or not obj[1:].isdigit():
        raise argparse.ArgumentTypeError("Cannot parse OSM ID. Expect format: [N|W|R]<id>.")

    return (obj[0].upper(), int(obj[1:]))


class UpdateRefresh:
    """\
    Recompute auxiliary data used by the indexing process.

    This sub-commands updates various static data and functions in the database.
    It usually needs to be run after changing various aspects of the
    configuration. The configuration documentation will mention the exact
    command to use in such case.

    Warning: the 'update' command must not be run in parallel with other update
             commands like 'replication' or 'add-data'.
    """
    def __init__(self) -> None:
        self.tokenizer: Optional[AbstractTokenizer] = None

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Data arguments')
        group.add_argument('--postcodes', action='store_true',
                           help='Update postcode centroid table')
        group.add_argument('--word-tokens', action='store_true',
                           help='Clean up search terms')
        group.add_argument('--word-counts', action='store_true',
                           help='Compute frequency of full-word search terms')
        group.add_argument('--address-levels', action='store_true',
                           help='Reimport address level configuration')
        group.add_argument('--functions', action='store_true',
                           help='Update the PL/pgSQL functions in the database')
        group.add_argument('--wiki-data', action='store_true',
                           help='Update Wikipedia/data importance numbers')
        group.add_argument('--secondary-importance', action='store_true',
                           help='Update secondary importance raster data')
        group.add_argument('--importance', action='store_true',
                           help='Recompute place importances (expensive!)')
        group.add_argument('--website', action='store_true',
                           help='DEPRECATED. This function has no function anymore'
                                ' and will be removed in a future version.')
        group.add_argument('--data-object', action='append',
                           type=_parse_osm_object, metavar='OBJECT',
                           help='Mark the given OSM object as requiring an update'
                                ' (format: [NWR]<id>)')
        group.add_argument('--data-area', action='append',
                           type=_parse_osm_object, metavar='OBJECT',
                           help='Mark the area around the given OSM object as requiring an update'
                                ' (format: [NWR]<id>)')

        group = parser.add_argument_group('Arguments for function refresh')
        group.add_argument('--no-diff-updates', action='store_false', dest='diffs',
                           help='Do not enable code for propagating updates')
        group.add_argument('--enable-debug-statements', action='store_true',
                           help='Enable debug warning statements in functions')
        
        group = parser.add_argument_group('Access control')
        group.add_argument('--ro-access', action='store_true',
                           help='Grant read-only database access to the web user')

    def run(self, args: NominatimArgs) -> int:
        from ..tools import refresh, postcodes
        from ..indexer.indexer import Indexer

        need_function_refresh = args.functions

        if args.postcodes:
            if postcodes.can_compute(args.config.get_libpq_dsn()):
                LOG.warning("Update postcodes centroid")
                tokenizer = self._get_tokenizer(args.config)
                postcodes.update_postcodes(args.config.get_libpq_dsn(),
                                           args.project_dir, tokenizer)
                indexer = Indexer(args.config.get_libpq_dsn(), tokenizer,
                                  args.threads or 1)
                asyncio.run(indexer.index_postcodes())
            else:
                LOG.error("The place table doesn't exist. "
                          "Postcode updates on a frozen database is not possible.")

        if args.word_tokens:
            LOG.warning('Updating word tokens')
            tokenizer = self._get_tokenizer(args.config)
            tokenizer.update_word_tokens()

        if args.word_counts:
            LOG.warning('Recompute word statistics')
            self._get_tokenizer(args.config).update_statistics(args.config,
                                                               threads=args.threads or 1)

        if args.address_levels:
            LOG.warning('Updating address levels')
            with connect(args.config.get_libpq_dsn()) as conn:
                refresh.load_address_levels_from_config(conn, args.config)

        # Attention: must come BEFORE functions
        if args.secondary_importance:
            with connect(args.config.get_libpq_dsn()) as conn:
                # If the table did not exist before, then the importance code
                # needs to be enabled.
                if not table_exists(conn, 'secondary_importance'):
                    args.functions = True

            LOG.warning('Import secondary importance raster data from %s', args.project_dir)
            if refresh.import_secondary_importance(args.config.get_libpq_dsn(),
                                                   args.project_dir) > 0:
                LOG.fatal('FATAL: Cannot update secondary importance raster data')
                return 1
            need_function_refresh = True

        if args.wiki_data:
            data_path = Path(args.config.WIKIPEDIA_DATA_PATH
                             or args.project_dir)
            LOG.warning('Import wikipedia article importance from %s', data_path)
            if refresh.import_wikipedia_articles(args.config.get_libpq_dsn(),
                                                 data_path) > 0:
                LOG.fatal('FATAL: Wikipedia importance file not found in %s', data_path)
                return 1
            need_function_refresh = True

        if need_function_refresh:
            LOG.warning('Create functions')
            with connect(args.config.get_libpq_dsn()) as conn:
                refresh.create_functions(conn, args.config,
                                         args.diffs, args.enable_debug_statements)
                self._get_tokenizer(args.config).update_sql_functions(args.config)

        # Attention: importance MUST come after wiki data import and after functions.
        if args.importance:
            LOG.warning('Update importance values for database')
            with connect(args.config.get_libpq_dsn()) as conn:
                refresh.recompute_importance(conn)

        if args.website:
            LOG.error('WARNING: Website setup is no longer required. '
                      'This function will be removed in future version of Nominatim.')

        if args.data_object or args.data_area:
            with connect(args.config.get_libpq_dsn()) as conn:
                for obj in args.data_object or []:
                    refresh.invalidate_osm_object(*obj, conn, recursive=False)
                for obj in args.data_area or []:
                    refresh.invalidate_osm_object(*obj, conn, recursive=True)
                conn.commit()

        if args.ro_access:
            LOG.warning("Granting read-only access to web user")
            grant_readonly_access(args.config)

        return 0

    def _get_tokenizer(self, config: Configuration) -> AbstractTokenizer:
        if self.tokenizer is None:
            from ..tokenizer import factory as tokenizer_factory

            self.tokenizer = tokenizer_factory.get_tokenizer_for_db(config)

        return self.tokenizer
