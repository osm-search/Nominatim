# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the 'export' subcommand.
"""
from typing import Optional, List, cast
import logging
import argparse
import asyncio
import csv
import sys

import sqlalchemy as sa

from nominatim.clicmd.args import NominatimArgs
import nominatim.api as napi
from nominatim.api.results import create_from_placex_row, ReverseResult, add_result_details
from nominatim.api.types import LookupDetails
from nominatim.errors import UsageError

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415
# Needed for SQLAlchemy
# pylint: disable=singleton-comparison

LOG = logging.getLogger()

RANK_RANGE_MAP = {
  'country': (4, 4),
  'state': (5, 9),
  'county': (10, 12),
  'city': (13, 16),
  'suburb': (17, 21),
  'street': (26, 26),
  'path': (27, 27)
}

RANK_TO_OUTPUT_MAP = {
    4: 'country',
    5: 'state', 6: 'state', 7: 'state', 8: 'state', 9: 'state',
    10: 'county', 11: 'county', 12: 'county',
    13: 'city', 14: 'city', 15: 'city', 16: 'city',
    17: 'suburb', 18: 'suburb', 19: 'suburb', 20: 'suburb', 21: 'suburb',
    26: 'street', 27: 'path'}

class QueryExport:
    """\
    Export places as CSV file from the database.


    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Output arguments')
        group.add_argument('--output-type', default='street',
                           choices=('country', 'state', 'county',
                                    'city', 'suburb', 'street', 'path'),
                           help='Type of places to output (default: street)')
        group.add_argument('--output-format',
                           default='street;suburb;city;county;state;country',
                           help=("Semicolon-separated list of address types "
                                 "(see --output-type). Additionally accepts:"
                                 "placeid,postcode"))
        group.add_argument('--language',
                           help=("Preferred language for output "
                                 "(use local name, if omitted)"))
        group = parser.add_argument_group('Filter arguments')
        group.add_argument('--restrict-to-country', metavar='COUNTRY_CODE',
                           help='Export only objects within country')
        group.add_argument('--restrict-to-osm-node', metavar='ID', type=int,
                           dest='node',
                           help='Export only children of this OSM node')
        group.add_argument('--restrict-to-osm-way', metavar='ID', type=int,
                           dest='way',
                           help='Export only children of this OSM way')
        group.add_argument('--restrict-to-osm-relation', metavar='ID', type=int,
                           dest='relation',
                           help='Export only children of this OSM relation')


    def run(self, args: NominatimArgs) -> int:
        return asyncio.run(export(args))


async def export(args: NominatimArgs) -> int:
    """ The actual export as a asynchronous function.
    """

    api = napi.NominatimAPIAsync(args.project_dir)

    try:
        output_range = RANK_RANGE_MAP[args.output_type]

        writer = init_csv_writer(args.output_format)

        async with api.begin() as conn, api.begin() as detail_conn:
            t = conn.t.placex

            sql = sa.select(t.c.place_id, t.c.parent_place_id,
                        t.c.osm_type, t.c.osm_id, t.c.name,
                        t.c.class_, t.c.type, t.c.admin_level,
                        t.c.address, t.c.extratags,
                        t.c.housenumber, t.c.postcode, t.c.country_code,
                        t.c.importance, t.c.wikipedia, t.c.indexed_date,
                        t.c.rank_address, t.c.rank_search,
                        t.c.centroid)\
                     .where(t.c.linked_place_id == None)\
                     .where(t.c.rank_address.between(*output_range))

            parent_place_id = await get_parent_id(conn, args.node, args.way, args.relation)
            if parent_place_id:
                taddr = conn.t.addressline

                sql = sql.join(taddr, taddr.c.place_id == t.c.place_id)\
                         .where(taddr.c.address_place_id == parent_place_id)\
                         .where(taddr.c.isaddress)

            if args.restrict_to_country:
                sql = sql.where(t.c.country_code == args.restrict_to_country.lower())

            results = []
            for row in await conn.execute(sql):
                result = create_from_placex_row(row, ReverseResult)
                if result is not None:
                    results.append(result)

                if len(results) == 1000:
                    await dump_results(detail_conn, results, writer, args.language)
                    results = []

            if results:
                await dump_results(detail_conn, results, writer, args.language)
    finally:
        await api.close()

    return 0


def init_csv_writer(output_format: str) -> 'csv.DictWriter[str]':
    fields = output_format.split(';')
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, extrasaction='ignore')
    writer.writeheader()

    return writer


async def dump_results(conn: napi.SearchConnection,
                       results: List[ReverseResult],
                       writer: 'csv.DictWriter[str]',
                       lang: Optional[str]) -> None:
    locale = napi.Locales([lang] if lang else None)
    await add_result_details(conn, results,
                             LookupDetails(address_details=True, locales=locale))


    for result in results:
        data = {'placeid': result.place_id,
                'postcode': result.postcode}

        for line in (result.address_rows or []):
            if line.isaddress and line.local_name:
                if line.category[1] == 'postcode':
                    data['postcode'] = line.local_name
                elif line.rank_address in RANK_TO_OUTPUT_MAP:
                    data[RANK_TO_OUTPUT_MAP[line.rank_address]] = line.local_name

        writer.writerow(data)


async def get_parent_id(conn: napi.SearchConnection, node_id: Optional[int],
                        way_id: Optional[int],
                        relation_id: Optional[int]) -> Optional[int]:
    """ Get the place ID for the given OSM object.
    """
    if node_id is not None:
        osm_type, osm_id = 'N', node_id
    elif way_id is not None:
        osm_type, osm_id = 'W', way_id
    elif relation_id is not None:
        osm_type, osm_id = 'R', relation_id
    else:
        return None

    t = conn.t.placex
    sql = sa.select(t.c.place_id).limit(1)\
            .where(t.c.osm_type == osm_type)\
            .where(t.c.osm_id == osm_id)\
            .where(t.c.rank_address > 0)\
            .order_by(t.c.rank_address)

    for result in await conn.execute(sql):
        return cast(int, result[0])

    raise UsageError(f'Cannot find a place {osm_type}{osm_id}.')
