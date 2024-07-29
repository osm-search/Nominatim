# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'index' subcommand.
"""
import argparse
import asyncio

import psutil

from ..db import status
from ..db.connection import connect
from .args import NominatimArgs

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415


class UpdateIndex:
    """\
    Reindex all new and modified data.

    Indexing is the process of computing the address and search terms for
    the places in the database. Every time data is added or changed, indexing
    needs to be run. Imports and replication updates automatically take care
    of indexing. For other cases, this function allows to run indexing manually.
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Filter arguments')
        group.add_argument('--boundaries-only', action='store_true',
                           help="""Index only administrative boundaries.""")
        group.add_argument('--no-boundaries', action='store_true',
                           help="""Index everything except administrative boundaries.""")
        group.add_argument('--minrank', '-r', type=int, metavar='RANK', default=0,
                           help='Minimum/starting rank')
        group.add_argument('--maxrank', '-R', type=int, metavar='RANK', default=30,
                           help='Maximum/finishing rank')


    def run(self, args: NominatimArgs) -> int:
        asyncio.run(self._do_index(args))

        if not args.no_boundaries and not args.boundaries_only \
           and args.minrank == 0 and args.maxrank == 30:
            with connect(args.config.get_libpq_dsn()) as conn:
                status.set_indexed(conn, True)

        return 0


    async def _do_index(self, args: NominatimArgs) -> None:
        from ..tokenizer import factory as tokenizer_factory

        tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
        from ..indexer.indexer import Indexer

        indexer = Indexer(args.config.get_libpq_dsn(), tokenizer,
                          args.threads or psutil.cpu_count() or 1)

        has_pending = True # run at least once
        while has_pending:
            if not args.no_boundaries:
                await indexer.index_boundaries(args.minrank, args.maxrank)
            if not args.boundaries_only:
                await indexer.index_by_rank(args.minrank, args.maxrank)
                await indexer.index_postcodes()
            has_pending = indexer.has_pending()
