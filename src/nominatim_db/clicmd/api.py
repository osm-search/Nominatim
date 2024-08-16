# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Subcommand definitions for API calls from the command line.
"""
from typing import Dict, Any, Optional, Type, Mapping
import argparse
import logging
import json
import sys
from functools import reduce

import nominatim_api as napi
from nominatim_api.v1.helpers import zoom_to_rank, deduplicate_results
from nominatim_api.server.content_types import CONTENT_JSON
import nominatim_api.logging as loglib
from ..errors import UsageError
from .args import NominatimArgs

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111

LOG = logging.getLogger()

STRUCTURED_QUERY = (
    ('amenity', 'name and/or type of POI'),
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

def _add_list_format(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group('Other options')
    group.add_argument('--list-formats', action='store_true',
                       help='List supported output formats and exit.')


def _add_api_output_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_argument_group('Output formatting')
    group.add_argument('--format', type=str, default='jsonv2',
                       help='Format of result (use --list-format to see supported formats)')
    for name, desc in EXTRADATA_PARAMS:
        group.add_argument('--' + name, action='store_true', help=desc)

    group.add_argument('--lang', '--accept-language', metavar='LANGS',
                       help='Preferred language order for presenting search results')
    group.add_argument('--polygon-output',
                       choices=['geojson', 'kml', 'svg', 'text'],
                       help='Output geometry of results as a GeoJSON, KML, SVG or WKT')
    group.add_argument('--polygon-threshold', type=float, default = 0.0,
                       metavar='TOLERANCE',
                       help=("Simplify output geometry."
                             "Parameter is difference tolerance in degrees."))


def _get_geometry_output(args: NominatimArgs) -> napi.GeometryFormat:
    """ Get the requested geometry output format in a API-compatible
        format.
    """
    if not args.polygon_output:
        return napi.GeometryFormat.NONE
    if args.polygon_output == 'geojson':
        return napi.GeometryFormat.GEOJSON
    if args.polygon_output == 'kml':
        return napi.GeometryFormat.KML
    if args.polygon_output == 'svg':
        return napi.GeometryFormat.SVG
    if args.polygon_output == 'text':
        return napi.GeometryFormat.TEXT

    try:
        return napi.GeometryFormat[args.polygon_output.upper()]
    except KeyError as exp:
        raise UsageError(f"Unknown polygon output format '{args.polygon_output}'.") from exp


def _get_locales(args: NominatimArgs, default: Optional[str]) -> napi.Locales:
    """ Get the locales from the language parameter.
    """
    if args.lang:
        return napi.Locales.from_accept_languages(args.lang)
    if default:
        return napi.Locales.from_accept_languages(default)

    return napi.Locales()


def _get_layers(args: NominatimArgs, default: napi.DataLayer) -> Optional[napi.DataLayer]:
    """ Get the list of selected layers as a DataLayer enum.
    """
    if not args.layers:
        return default

    return reduce(napi.DataLayer.__or__,
                  (napi.DataLayer[s.upper()] for s in args.layers))


def _list_formats(formatter: napi.FormatDispatcher, rtype: Type[Any]) -> int:
    for fmt in formatter.list_formats(rtype):
        print(fmt)
    print('debug')

    return 0


def _print_output(formatter: napi.FormatDispatcher, result: Any,
                  fmt: str, options: Mapping[str, Any]) -> None:
    output = formatter.format_result(result, fmt, options)
    if formatter.get_content_type(fmt) == CONTENT_JSON:
        # reformat the result, so it is pretty-printed
        json.dump(json.loads(output), sys.stdout, indent=4, ensure_ascii=False)
    else:
        sys.stdout.write(output)
    sys.stdout.write('\n')

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
        group.add_argument('--limit', type=int, default=10,
                           help='Limit the number of returned results')
        group.add_argument('--viewbox', metavar='X1,Y1,X2,Y2',
                           help='Preferred area to find search results')
        group.add_argument('--bounded', action='store_true',
                           help='Strictly restrict results to viewbox area')
        group.add_argument('--no-dedupe', action='store_false', dest='dedupe',
                           help='Do not remove duplicates from the result list')
        _add_list_format(parser)


    def run(self, args: NominatimArgs) -> int:
        formatter = napi.load_format_dispatcher('v1', args.project_dir)

        if args.list_formats:
            return _list_formats(formatter, napi.SearchResults)

        if args.format == 'debug':
            loglib.set_log_output('text')
        elif not formatter.supports_format(napi.SearchResults, args.format):
            raise UsageError(f"Unsupported format '{args.format}'. "
                             'Use --list-formats to see supported formats.')

        api = napi.NominatimAPI(args.project_dir)
        params: Dict[str, Any] = {'max_results': args.limit + min(args.limit, 10),
                                  'address_details': True, # needed for display name
                                  'geometry_output': _get_geometry_output(args),
                                  'geometry_simplification': args.polygon_threshold,
                                  'countries': args.countrycodes,
                                  'excluded': args.exclude_place_ids,
                                  'viewbox': args.viewbox,
                                  'bounded_viewbox': args.bounded,
                                  'locales': _get_locales(args, api.config.DEFAULT_LANGUAGE)
                                 }

        if args.query:
            results = api.search(args.query, **params)
        else:
            results = api.search_address(amenity=args.amenity,
                                         street=args.street,
                                         city=args.city,
                                         county=args.county,
                                         state=args.state,
                                         postalcode=args.postalcode,
                                         country=args.country,
                                         **params)

        if args.dedupe and len(results) > 1:
            results = deduplicate_results(results, args.limit)

        if args.format == 'debug':
            print(loglib.get_and_disable())
            return 0

        _print_output(formatter, results, args.format,
                      {'extratags': args.extratags,
                       'namedetails': args.namedetails,
                       'addressdetails': args.addressdetails})
        return 0


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
        group.add_argument('--lat', type=float,
                           help='Latitude of coordinate to look up (in WGS84)')
        group.add_argument('--lon', type=float,
                           help='Longitude of coordinate to look up (in WGS84)')
        group.add_argument('--zoom', type=int,
                           help='Level of detail required for the address')
        group.add_argument('--layer', metavar='LAYER',
                           choices=[n.name.lower() for n in napi.DataLayer if n.name],
                           action='append', required=False, dest='layers',
                           help='OSM id to lookup in format <NRW><id> (may be repeated)')

        _add_api_output_arguments(parser)
        _add_list_format(parser)


    def run(self, args: NominatimArgs) -> int:
        formatter = napi.load_format_dispatcher('v1', args.project_dir)

        if args.list_formats:
            return _list_formats(formatter, napi.ReverseResults)

        if args.format == 'debug':
            loglib.set_log_output('text')
        elif not formatter.supports_format(napi.ReverseResults, args.format):
            raise UsageError(f"Unsupported format '{args.format}'. "
                             'Use --list-formats to see supported formats.')

        if args.lat is None or args.lon is None:
            raise UsageError("lat' and 'lon' parameters are required.")

        api = napi.NominatimAPI(args.project_dir)
        result = api.reverse(napi.Point(args.lon, args.lat),
                             max_rank=zoom_to_rank(args.zoom or 18),
                             layers=_get_layers(args, napi.DataLayer.ADDRESS | napi.DataLayer.POI),
                             address_details=True, # needed for display name
                             geometry_output=_get_geometry_output(args),
                             geometry_simplification=args.polygon_threshold,
                             locales=_get_locales(args, api.config.DEFAULT_LANGUAGE))

        if args.format == 'debug':
            print(loglib.get_and_disable())
            return 0

        if result:
            _print_output(formatter, napi.ReverseResults([result]), args.format,
                          {'extratags': args.extratags,
                           'namedetails': args.namedetails,
                           'addressdetails': args.addressdetails})

            return 0

        LOG.error("Unable to geocode.")
        return 42



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
                           action='append', dest='ids',
                           help='OSM id to lookup in format <NRW><id> (may be repeated)')

        _add_api_output_arguments(parser)
        _add_list_format(parser)


    def run(self, args: NominatimArgs) -> int:
        formatter = napi.load_format_dispatcher('v1', args.project_dir)

        if args.list_formats:
            return _list_formats(formatter, napi.ReverseResults)

        if args.format == 'debug':
            loglib.set_log_output('text')
        elif not formatter.supports_format(napi.ReverseResults, args.format):
            raise UsageError(f"Unsupported format '{args.format}'. "
                             'Use --list-formats to see supported formats.')

        if args.ids is None:
            raise UsageError("'id' parameter required.")

        places = [napi.OsmID(o[0], int(o[1:])) for o in args.ids]

        api = napi.NominatimAPI(args.project_dir)
        results = api.lookup(places,
                             address_details=True, # needed for display name
                             geometry_output=_get_geometry_output(args),
                             geometry_simplification=args.polygon_threshold or 0.0,
                             locales=_get_locales(args, api.config.DEFAULT_LANGUAGE))

        if args.format == 'debug':
            print(loglib.get_and_disable())
            return 0

        _print_output(formatter, results, args.format,
                      {'extratags': args.extratags,
                       'namedetails': args.namedetails,
                       'addressdetails': args.addressdetails})
        return 0


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
        group.add_argument('--node', '-n', type=int,
                           help="Look up the OSM node with the given ID.")
        group.add_argument('--way', '-w', type=int,
                           help="Look up the OSM way with the given ID.")
        group.add_argument('--relation', '-r', type=int,
                           help="Look up the OSM relation with the given ID.")
        group.add_argument('--place_id', '-p', type=int,
                           help='Database internal identifier of the OSM object to look up')
        group.add_argument('--class', dest='object_class',
                           help=("Class type to disambiguated multiple entries "
                                 "of the same object."))

        group = parser.add_argument_group('Output arguments')
        group.add_argument('--format', type=str, default='json',
                           help='Format of result (use --list-formats to see supported formats)')
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
        _add_list_format(parser)


    def run(self, args: NominatimArgs) -> int:
        formatter = napi.load_format_dispatcher('v1', args.project_dir)

        if args.list_formats:
            return _list_formats(formatter, napi.DetailedResult)

        if args.format == 'debug':
            loglib.set_log_output('text')
        elif not formatter.supports_format(napi.DetailedResult, args.format):
            raise UsageError(f"Unsupported format '{args.format}'. "
                             'Use --list-formats to see supported formats.')

        place: napi.PlaceRef
        if args.node:
            place = napi.OsmID('N', args.node, args.object_class)
        elif args.way:
            place = napi.OsmID('W', args.way, args.object_class)
        elif args.relation:
            place = napi.OsmID('R', args.relation, args.object_class)
        elif  args.place_id is not None:
            place = napi.PlaceID(args.place_id)
        else:
            raise UsageError('One of the arguments --node/-n --way/-w '
                             '--relation/-r --place_id/-p is required/')

        api = napi.NominatimAPI(args.project_dir)
        locales = _get_locales(args, api.config.DEFAULT_LANGUAGE)
        result = api.details(place,
                             address_details=args.addressdetails,
                             linked_places=args.linkedplaces,
                             parented_places=args.hierarchy,
                             keywords=args.keywords,
                             geometry_output=napi.GeometryFormat.GEOJSON
                                             if args.polygon_geojson
                                             else napi.GeometryFormat.NONE,
                            locales=locales)

        if args.format == 'debug':
            print(loglib.get_and_disable())
            return 0

        if result:
            _print_output(formatter, result, args.format or 'json',
                          {'locales': locales,
                           'group_hierarchy': args.group_hierarchy})
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
        group = parser.add_argument_group('API parameters')
        group.add_argument('--format', type=str, default='text',
                           help='Format of result (use --list-formats to see supported formats)')
        _add_list_format(parser)


    def run(self, args: NominatimArgs) -> int:
        formatter = napi.load_format_dispatcher('v1', args.project_dir)

        if args.list_formats:
            return _list_formats(formatter, napi.StatusResult)

        if args.format == 'debug':
            loglib.set_log_output('text')
        elif not formatter.supports_format(napi.StatusResult, args.format):
            raise UsageError(f"Unsupported format '{args.format}'. "
                             'Use --list-formats to see supported formats.')

        status = napi.NominatimAPI(args.project_dir).status()

        if args.format == 'debug':
            print(loglib.get_and_disable())
            return 0

        _print_output(formatter, status, args.format, {})

        return 0
