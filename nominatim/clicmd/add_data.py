# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'add-data' subcommand.
"""
from typing import cast
import argparse
import logging

import psutil

from nominatim.clicmd.args import NominatimArgs

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

LOG = logging.getLogger()

class UpdateAddData:
    """\
    Add additional data from a file or an online source.

    This command allows to add or update the search data in the database.
    The data can come either from an OSM file or single OSM objects can
    directly be downloaded from the OSM API. This function only loads the
    data into the database. Afterwards it still needs to be integrated
    in the search index. Use the `nominatim index` command for that.

    The command can also be used to add external non-OSM data to the
    database. At the moment the only supported format is TIGER housenumber
    data. See the online documentation at
    https://nominatim.org/release-docs/latest/admin/Import/#installing-tiger-housenumber-data-for-the-us
    for more information.
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group_name = parser.add_argument_group('Source')
        group1 = group_name.add_mutually_exclusive_group(required=True)
        group1.add_argument('--file', metavar='FILE',
                            help='Import data from an OSM file or diff file')
        group1.add_argument('--diff', metavar='FILE',
                            help='Import data from an OSM diff file (deprecated: use --file)')
        group1.add_argument('--node', metavar='ID', type=int,
                            help='Import a single node from the API')
        group1.add_argument('--way', metavar='ID', type=int,
                            help='Import a single way from the API')
        group1.add_argument('--relation', metavar='ID', type=int,
                            help='Import a single relation from the API')
        group1.add_argument('--tiger-data', metavar='DIR',
                            help='Add housenumbers from the US TIGER census database')
        group2 = parser.add_argument_group('Extra arguments')
        group2.add_argument('--use-main-api', action='store_true',
                            help='Use OSM API instead of Overpass to download objects')
        group2.add_argument('--osm2pgsql-cache', metavar='SIZE', type=int,
                            help='Size of cache to be used by osm2pgsql (in MB)')
        group2.add_argument('--socket-timeout', dest='socket_timeout', type=int, default=60,
                            help='Set timeout for file downloads')


    def run(self, args: NominatimArgs) -> int:
        from nominatim.tokenizer import factory as tokenizer_factory
        from nominatim.tools import tiger_data, add_osm_data

        if args.tiger_data:
            tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
            return tiger_data.add_tiger_data(args.tiger_data,
                                             args.config,
                                             args.threads or psutil.cpu_count()  or 1,
                                             tokenizer)

        osm2pgsql_params = args.osm2pgsql_options(default_cache=1000, default_threads=1)
        if args.file or args.diff:
            return add_osm_data.add_data_from_file(cast(str, args.file or args.diff),
                                                   osm2pgsql_params)

        if args.node:
            return add_osm_data.add_osm_object('node', args.node,
                                               args.use_main_api,
                                               osm2pgsql_params)

        if args.way:
            return add_osm_data.add_osm_object('way', args.way,
                                               args.use_main_api,
                                               osm2pgsql_params)

        if args.relation:
            return add_osm_data.add_osm_object('relation', args.relation,
                                               args.use_main_api,
                                               osm2pgsql_params)

        return 0
