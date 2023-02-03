# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Subcommand definitions for API calls from the command line.
"""
from typing import Mapping, Dict
import argparse
import logging
import json
import sys

from nominatim.tools.exec_utils import run_api_script
from nominatim.errors import UsageError
from nominatim.clicmd.args import NominatimArgs
import nominatim.api as napi
import nominatim.api.v1 as api_output

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111

LOG = logging.getLogger()

STRUCTURED_QUERY = (
    ('street', 'housenumber and street'),
    ('city', 'city, town or village'),
    ('county', 'county'),
    ('state', 'state'),
    ('country', 'country'),
    ('postalcode', 'postcode')
)

EXTRADATA_PARAMS = (
    ('addressdetails', 'Include a breakdown of the address into elements'),
    ('extratags', ("Include additional information if available "
                   "(e.g. wikipedia link, opening hours)")),
    ('namedetails', 'Include a list of alternative names')
)

def _add_api_output_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group('Output arguments')
    group.add_argument('--format', default='jsonv2',
                       choices=['xml', 'json', 'jsonv2', 'geojson', 'geocodejson'],
                       help='Format of result')
    for name, desc in EXTRADATA_PARAMS:
        group.add_argument('--' + name, action='store_true', help=desc)

    group.add_argument('--lang', '--accept-language', metavar='LANGS',
                       help='Preferred language order for presenting search results')
    group.add_argument('--polygon-output',
                       choices=['geojson', 'kml', 'svg', 'text'],
                       help='Output geometry of results as a GeoJSON, KML, SVG or WKT')
    group.add_argument('--polygon-threshold', type=float, metavar='TOLERANCE',
                       help=("Simplify output geometry."
                             "Parameter is difference tolerance in degrees."))


def _run_api(endpoint: str, args: NominatimArgs, params: Mapping[str, object]) -> int:
    script_file = args.project_dir / 'website' / (endpoint + '.php')

    if not script_file.exists():
        LOG.error("Cannot find API script file.\n\n"
                  "Make sure to run 'nominatim' from the project directory \n"
                  "or use the option --project-dir.")
        raise UsageError("API script not found.")

    return run_api_script(endpoint, args.project_dir,
                          phpcgi_bin=args.phpcgi_path, params=params)

class APISearch:
    """\
    Execute a search query.

    This command works exactly the same as if calling the /search endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Search/
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Query arguments')
        group.add_argument('--query',
                           help='Free-form query string')
        for name, desc in STRUCTURED_QUERY:
            group.add_argument('--' + name, help='Structured query: ' + desc)

        _add_api_output_arguments(parser)

        group = parser.add_argument_group('Result limitation')
        group.add_argument('--countrycodes', metavar='CC,..',
                           help='Limit search results to one or more countries')
        group.add_argument('--exclude_place_ids', metavar='ID,..',
                           help='List of search object to be excluded')
        group.add_argument('--limit', type=int,
                           help='Limit the number of returned results')
        group.add_argument('--viewbox', metavar='X1,Y1,X2,Y2',
                           help='Preferred area to find search results')
        group.add_argument('--bounded', action='store_true',
                           help='Strictly restrict results to viewbox area')

        group = parser.add_argument_group('Other arguments')
        group.add_argument('--no-dedupe', action='store_false', dest='dedupe',
                           help='Do not remove duplicates from the result list')


    def run(self, args: NominatimArgs) -> int:
        params: Dict[str, object]
        if args.query:
            params = dict(q=args.query)
        else:
            params = {k: getattr(args, k) for k, _ in STRUCTURED_QUERY if getattr(args, k)}

        for param, _ in EXTRADATA_PARAMS:
            if getattr(args, param):
                params[param] = '1'
        for param in ('format', 'countrycodes', 'exclude_place_ids', 'limit', 'viewbox'):
            if getattr(args, param):
                params[param] = getattr(args, param)
        if args.lang:
            params['accept-language'] = args.lang
        if args.polygon_output:
            params['polygon_' + args.polygon_output] = '1'
        if args.polygon_threshold:
            params['polygon_threshold'] = args.polygon_threshold
        if args.bounded:
            params['bounded'] = '1'
        if not args.dedupe:
            params['dedupe'] = '0'

        return _run_api('search', args, params)

class APIReverse:
    """\
    Execute API reverse query.

    This command works exactly the same as if calling the /reverse endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Reverse/
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Query arguments')
        group.add_argument('--lat', type=float, required=True,
                           help='Latitude of coordinate to look up (in WGS84)')
        group.add_argument('--lon', type=float, required=True,
                           help='Longitude of coordinate to look up (in WGS84)')
        group.add_argument('--zoom', type=int,
                           help='Level of detail required for the address')

        _add_api_output_arguments(parser)


    def run(self, args: NominatimArgs) -> int:
        params = dict(lat=args.lat, lon=args.lon, format=args.format)
        if args.zoom is not None:
            params['zoom'] = args.zoom

        for param, _ in EXTRADATA_PARAMS:
            if getattr(args, param):
                params[param] = '1'
        if args.lang:
            params['accept-language'] = args.lang
        if args.polygon_output:
            params['polygon_' + args.polygon_output] = '1'
        if args.polygon_threshold:
            params['polygon_threshold'] = args.polygon_threshold

        return _run_api('reverse', args, params)


class APILookup:
    """\
    Execute API lookup query.

    This command works exactly the same as if calling the /lookup endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Lookup/
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Query arguments')
        group.add_argument('--id', metavar='OSMID',
                           action='append', required=True, dest='ids',
                           help='OSM id to lookup in format <NRW><id> (may be repeated)')

        _add_api_output_arguments(parser)


    def run(self, args: NominatimArgs) -> int:
        params: Dict[str, object] = dict(osm_ids=','.join(args.ids), format=args.format)

        for param, _ in EXTRADATA_PARAMS:
            if getattr(args, param):
                params[param] = '1'
        if args.lang:
            params['accept-language'] = args.lang
        if args.polygon_output:
            params['polygon_' + args.polygon_output] = '1'
        if args.polygon_threshold:
            params['polygon_threshold'] = args.polygon_threshold

        return _run_api('lookup', args, params)


class APIDetails:
    """\
    Execute API details query.

    This command works exactly the same as if calling the /details endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Details/
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        group = parser.add_argument_group('Query arguments')
        objs = group.add_mutually_exclusive_group(required=True)
        objs.add_argument('--node', '-n', type=int,
                          help="Look up the OSM node with the given ID.")
        objs.add_argument('--way', '-w', type=int,
                          help="Look up the OSM way with the given ID.")
        objs.add_argument('--relation', '-r', type=int,
                          help="Look up the OSM relation with the given ID.")
        objs.add_argument('--place_id', '-p', type=int,
                          help='Database internal identifier of the OSM object to look up')
        group.add_argument('--class', dest='object_class',
                           help=("Class type to disambiguated multiple entries "
                                 "of the same object."))

        group = parser.add_argument_group('Output arguments')
        group.add_argument('--addressdetails', action='store_true',
                           help='Include a breakdown of the address into elements')
        group.add_argument('--keywords', action='store_true',
                           help='Include a list of name keywords and address keywords')
        group.add_argument('--linkedplaces', action='store_true',
                           help='Include a details of places that are linked with this one')
        group.add_argument('--hierarchy', action='store_true',
                           help='Include details of places lower in the address hierarchy')
        group.add_argument('--group_hierarchy', action='store_true',
                           help='Group the places by type')
        group.add_argument('--polygon_geojson', action='store_true',
                           help='Include geometry of result')
        group.add_argument('--lang', '--accept-language', metavar='LANGS',
                           help='Preferred language order for presenting search results')


    def run(self, args: NominatimArgs) -> int:
        place: napi.PlaceRef
        if args.node:
            place = napi.OsmID('N', args.node, args.object_class)
        elif args.way:
            place = napi.OsmID('W', args.way, args.object_class)
        elif args.relation:
            place = napi.OsmID('R', args.relation, args.object_class)
        else:
            assert args.place_id is not None
            place = napi.PlaceID(args.place_id)

        api = napi.NominatimAPI(args.project_dir)

        details = napi.LookupDetails(address_details=args.addressdetails,
                                     linked_places=args.linkedplaces,
                                     parented_places=args.hierarchy,
                                     keywords=args.keywords)
        if args.polygon_geojson:
            details.geometry_output = napi.GeometryFormat.GEOJSON

        if args.lang:
            locales = napi.Locales.from_accept_languages(args.lang)
        elif api.config.DEFAULT_LANGUAGE:
            locales = napi.Locales.from_accept_languages(api.config.DEFAULT_LANGUAGE)
        else:
            locales = napi.Locales()

        result = api.lookup(place, details)

        if result:
            output = api_output.format_result(
                        result,
                        'details-json',
                        {'locales': locales,
                         'group_hierarchy': args.group_hierarchy})
            # reformat the result, so it is pretty-printed
            json.dump(json.loads(output), sys.stdout, indent=4)
            sys.stdout.write('\n')

            return 0

        LOG.error("Object not found in database.")
        return 42


class APIStatus:
    """
    Execute API status query.

    This command works exactly the same as if calling the /status endpoint on
    the web API. See the online documentation for more details on the
    various parameters:
    https://nominatim.org/release-docs/latest/api/Status/
    """

    def add_args(self, parser: argparse.ArgumentParser) -> None:
        formats = api_output.list_formats(napi.StatusResult)
        group = parser.add_argument_group('API parameters')
        group.add_argument('--format', default=formats[0], choices=formats,
                           help='Format of result')


    def run(self, args: NominatimArgs) -> int:
        status = napi.NominatimAPI(args.project_dir).status()
        print(api_output.format_result(status, args.format, {}))
        return 0
