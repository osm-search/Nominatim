# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'index' subcommand.
"""
import argparse

import psutil

from nominatim.db import status
from nominatim.db.connection import connect
from nominatim.clicmd.args import NominatimArgs

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
        from ..indexer.indexer import Indexer
        from ..tokenizer import factory as tokenizer_factory

        tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)

        indexer = Indexer(args.config.get_libpq_dsn(), tokenizer,
                          args.threads or psutil.cpu_count() or 1)

        if not args.no_boundaries:
            indexer.index_boundaries(args.minrank, args.maxrank)
        if not args.boundaries_only:
            indexer.index_by_rank(args.minrank, args.maxrank)

        if not args.no_boundaries and not args.boundaries_only \
           and args.minrank == 0 and args.maxrank == 30:
            with connect(args.config.get_libpq_dsn()) as conn:
                status.set_indexed(conn, True)

        return 0
