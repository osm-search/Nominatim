# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Generic part of the server implementation of the v1 API.
Combine with the scaffolding provided for the various Python ASGI frameworks.
"""
from typing import Optional, Any, Type, Callable, NoReturn, Dict, cast
from functools import reduce
import abc
import dataclasses
import math
from urllib.parse import urlencode

import sqlalchemy as sa

from ..errors import UsageError
from ..config import Configuration
from .. import logging as loglib
from ..core import NominatimAPIAsync
from .format import dispatch as formatting
from .format import RawDataList
from ..types import DataLayer, GeometryFormat, PlaceRef, PlaceID, OsmID, Point
from ..status import StatusResult
from ..results import DetailedResult, ReverseResults, SearchResult, SearchResults
from ..localization import Locales
from . import helpers

CONTENT_TEXT = 'text/plain; charset=utf-8'
CONTENT_XML = 'text/xml; charset=utf-8'
CONTENT_HTML = 'text/html; charset=utf-8'
CONTENT_JSON = 'application/json; charset=utf-8'

CONTENT_TYPE = {'text': CONTENT_TEXT, 'xml': CONTENT_XML, 'debug': CONTENT_HTML}

class ASGIAdaptor(abc.ABC):
    """ Adapter class for the different ASGI frameworks.
        Wraps functionality over concrete requests and responses.
    """
    content_type: str = CONTENT_TEXT

    @abc.abstractmethod
    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """ Return an input parameter as a string. If the parameter was
            not provided, return the 'default' value.
        """

    @abc.abstractmethod
    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """ Return a HTTP header parameter as a string. If the parameter was
            not provided, return the 'default' value.
        """


    @abc.abstractmethod
    def error(self, msg: str, status: int = 400) -> Exception:
        """ Construct an appropriate exception from the given error message.
            The exception must result in a HTTP error with the given status.
        """


    @abc.abstractmethod
    def create_response(self, status: int, output: str, num_results: int) -> Any:
        """ Create a response from the given parameters. The result will
            be returned by the endpoint functions. The adaptor may also
            return None when the response is created internally with some
            different means.

            The response must return the HTTP given status code 'status', set
            the HTTP content-type headers to the string provided and the
            body of the response to 'output'.
        """

    @abc.abstractmethod
    def base_uri(self) -> str:
        """ Return the URI of the original request.
        """


    @abc.abstractmethod
    def config(self) -> Configuration:
        """ Return the current configuration object.
        """


    def get_int(self, name: str, default: Optional[int] = None) -> int:
        """ Return an input parameter as an int. Raises an exception if
            the parameter is given but not in an integer format.

            If 'default' is given, then it will be returned when the parameter
            is missing completely. When 'default' is None, an error will be
            raised on a missing parameter.
        """
        value = self.get(name)

        if value is None:
            if default is not None:
                return default

            self.raise_error(f"Parameter '{name}' missing.")

        try:
            intval = int(value)
        except ValueError:
            self.raise_error(f"Parameter '{name}' must be a number.")

        return intval


    def get_float(self, name: str, default: Optional[float] = None) -> float:
        """ Return an input parameter as a flaoting-point number. Raises an
            exception if the parameter is given but not in an float format.

            If 'default' is given, then it will be returned when the parameter
            is missing completely. When 'default' is None, an error will be
            raised on a missing parameter.
        """
        value = self.get(name)

        if value is None:
            if default is not None:
                return default

            self.raise_error(f"Parameter '{name}' missing.")

        try:
            fval = float(value)
        except ValueError:
            self.raise_error(f"Parameter '{name}' must be a number.")

        if math.isnan(fval) or math.isinf(fval):
            self.raise_error(f"Parameter '{name}' must be a number.")

        return fval


    def get_bool(self, name: str, default: Optional[bool] = None) -> bool:
        """ Return an input parameter as bool. Only '0' is accepted as
            an input for 'false' all other inputs will be interpreted as 'true'.

            If 'default' is given, then it will be returned when the parameter
            is missing completely. When 'default' is None, an error will be
            raised on a missing parameter.
        """
        value = self.get(name)

        if value is None:
            if default is not None:
                return default

            self.raise_error(f"Parameter '{name}' missing.")

        return value != '0'


    def raise_error(self, msg: str, status: int = 400) -> NoReturn:
        """ Raise an exception resulting in the given HTTP status and
            message. The message will be formatted according to the
            output format chosen by the request.
        """
        if self.content_type == CONTENT_XML:
            msg = f"""<?xml version="1.0" encoding="UTF-8" ?>
                      <error>
                        <code>{status}</code>
                        <message>{msg}</message>
                      </error>
                   """
        elif self.content_type == CONTENT_JSON:
            msg = f"""{{"error":{{"code":{status},"message":"{msg}"}}}}"""
        elif self.content_type == CONTENT_HTML:
            loglib.log().section('Execution error')
            loglib.log().var_dump('Status', status)
            loglib.log().var_dump('Message', msg)
            msg = loglib.get_and_disable()

        raise self.error(msg, status)


def build_response(adaptor: ASGIAdaptor, output: str, status: int = 200,
                   num_results: int = 0) -> Any:
    """ Create a response from the given output. Wraps a JSONP function
        around the response, if necessary.
    """
    if adaptor.content_type == CONTENT_JSON and status == 200:
        jsonp = adaptor.get('json_callback')
        if jsonp is not None:
            if any(not part.isidentifier() for part in jsonp.split('.')):
                adaptor.raise_error('Invalid json_callback value')
            output = f"{jsonp}({output})"
            adaptor.content_type = 'application/javascript; charset=utf-8'

    return adaptor.create_response(status, output, num_results)


def get_accepted_languages(adaptor: ASGIAdaptor) -> str:
    """ Return the accepted languages.
    """
    return adaptor.get('accept-language')\
           or adaptor.get_header('accept-language')\
           or adaptor.config().DEFAULT_LANGUAGE


def setup_debugging(adaptor: ASGIAdaptor) -> bool:
    """ Set up collection of debug information if requested.

        Return True when debugging was requested.
    """
    if adaptor.get_bool('debug', False):
        loglib.set_log_output('html')
        adaptor.content_type = CONTENT_HTML
        return True

    return False


def get_layers(adaptor: ASGIAdaptor) -> Optional[DataLayer]:
    """ Return a parsed version of the layer parameter.
    """
    param = adaptor.get('layer', None)
    if param is None:
        return None

    return cast(DataLayer,
                reduce(DataLayer.__or__,
                       (getattr(DataLayer, s.upper()) for s in param.split(','))))


def parse_format(adaptor: ASGIAdaptor, result_type: Type[Any], default: str) -> str:
    """ Get and check the 'format' parameter and prepare the formatter.
        `result_type` is the type of result to be returned by the function
        and `default` the format value to assume when no parameter is present.
    """
    fmt = adaptor.get('format', default=default)
    assert fmt is not None

    if not formatting.supports_format(result_type, fmt):
        adaptor.raise_error("Parameter 'format' must be one of: " +
                          ', '.join(formatting.list_formats(result_type)))

    adaptor.content_type = CONTENT_TYPE.get(fmt, CONTENT_JSON)
    return fmt


def parse_geometry_details(adaptor: ASGIAdaptor, fmt: str) -> Dict[str, Any]:
    """ Create details structure from the supplied geometry parameters.
    """
    numgeoms = 0
    output = GeometryFormat.NONE
    if adaptor.get_bool('polygon_geojson', False):
        output |= GeometryFormat.GEOJSON
        numgeoms += 1
    if fmt not in ('geojson', 'geocodejson'):
        if adaptor.get_bool('polygon_text', False):
            output |= GeometryFormat.TEXT
            numgeoms += 1
        if adaptor.get_bool('polygon_kml', False):
            output |= GeometryFormat.KML
            numgeoms += 1
        if adaptor.get_bool('polygon_svg', False):
            output |= GeometryFormat.SVG
            numgeoms += 1

    if numgeoms > adaptor.config().get_int('POLYGON_OUTPUT_MAX_TYPES'):
        adaptor.raise_error('Too many polygon output options selected.')

    return {'address_details': True,
            'geometry_simplification': adaptor.get_float('polygon_threshold', 0.0),
            'geometry_output': output
           }


async def status_endpoint(api: NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /status endpoint. See API docs for details.
    """
    result = await api.status()

    fmt = parse_format(params, StatusResult, 'text')

    if fmt == 'text' and result.status:
        status_code = 500
    else:
        status_code = 200

    return build_response(params, formatting.format_result(result, fmt, {}),
                                 status=status_code)


async def details_endpoint(api: NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /details endpoint. See API docs for details.
    """
    fmt = parse_format(params, DetailedResult, 'json')
    place_id = params.get_int('place_id', 0)
    place: PlaceRef
    if place_id:
        place = PlaceID(place_id)
    else:
        osmtype = params.get('osmtype')
        if osmtype is None:
            params.raise_error("Missing ID parameter 'place_id' or 'osmtype'.")
        place = OsmID(osmtype, params.get_int('osmid'), params.get('class'))

    debug = setup_debugging(params)

    locales = Locales.from_accept_languages(get_accepted_languages(params))

    result = await api.details(place,
                               address_details=params.get_bool('addressdetails', False),
                               linked_places=params.get_bool('linkedplaces', True),
                               parented_places=params.get_bool('hierarchy', False),
                               keywords=params.get_bool('keywords', False),
                               geometry_output = GeometryFormat.GEOJSON
                                                 if params.get_bool('polygon_geojson', False)
                                                 else GeometryFormat.NONE,
                               locales=locales
                              )

    if debug:
        return build_response(params, loglib.get_and_disable())

    if result is None:
        params.raise_error('No place with that OSM ID found.', status=404)

    output = formatting.format_result(result, fmt,
                 {'locales': locales,
                  'group_hierarchy': params.get_bool('group_hierarchy', False),
                  'icon_base_url': params.config().MAPICON_URL})

    return build_response(params, output, num_results=1)


async def reverse_endpoint(api: NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /reverse endpoint. See API docs for details.
    """
    fmt = parse_format(params, ReverseResults, 'xml')
    debug = setup_debugging(params)
    coord = Point(params.get_float('lon'), params.get_float('lat'))

    details = parse_geometry_details(params, fmt)
    details['max_rank'] = helpers.zoom_to_rank(params.get_int('zoom', 18))
    details['layers'] = get_layers(params)
    details['locales'] = Locales.from_accept_languages(get_accepted_languages(params))

    result = await api.reverse(coord, **details)

    if debug:
        return build_response(params, loglib.get_and_disable(), num_results=1 if result else 0)

    if fmt == 'xml':
        queryparts = {'lat': str(coord.lat), 'lon': str(coord.lon), 'format': 'xml'}
        zoom = params.get('zoom', None)
        if zoom:
            queryparts['zoom'] = zoom
        query = urlencode(queryparts)
    else:
        query = ''

    fmt_options = {'query': query,
                   'extratags': params.get_bool('extratags', False),
                   'namedetails': params.get_bool('namedetails', False),
                   'addressdetails': params.get_bool('addressdetails', True)}

    output = formatting.format_result(ReverseResults([result] if result else []),
                                      fmt, fmt_options)

    return build_response(params, output, num_results=1 if result else 0)


async def lookup_endpoint(api: NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /lookup endpoint. See API docs for details.
    """
    fmt = parse_format(params, SearchResults, 'xml')
    debug = setup_debugging(params)
    details = parse_geometry_details(params, fmt)
    details['locales'] = Locales.from_accept_languages(get_accepted_languages(params))

    places = []
    for oid in (params.get('osm_ids') or '').split(','):
        oid = oid.strip()
        if len(oid) > 1 and oid[0] in 'RNWrnw' and oid[1:].isdigit():
            places.append(OsmID(oid[0].upper(), int(oid[1:])))

    if len(places) > params.config().get_int('LOOKUP_MAX_COUNT'):
        params.raise_error('Too many object IDs.')

    if places:
        results = await api.lookup(places, **details)
    else:
        results = SearchResults()

    if debug:
        return build_response(params, loglib.get_and_disable(), num_results=len(results))

    fmt_options = {'extratags': params.get_bool('extratags', False),
                   'namedetails': params.get_bool('namedetails', False),
                   'addressdetails': params.get_bool('addressdetails', True)}

    output = formatting.format_result(results, fmt, fmt_options)

    return build_response(params, output, num_results=len(results))


async def _unstructured_search(query: str, api: NominatimAPIAsync,
                              details: Dict[str, Any]) -> SearchResults:
    if not query:
        return SearchResults()

    # Extract special format for coordinates from query.
    query, x, y = helpers.extract_coords_from_query(query)
    if x is not None:
        assert y is not None
        details['near'] = Point(x, y)
        details['near_radius'] = 0.1

    # If no query is left, revert to reverse search.
    if x is not None and not query:
        result = await api.reverse(details['near'], **details)
        if not result:
            return SearchResults()

        return SearchResults(
                  [SearchResult(**{f.name: getattr(result, f.name)
                                   for f in dataclasses.fields(SearchResult)
                                   if hasattr(result, f.name)})])

    query, cls, typ = helpers.extract_category_from_query(query)
    if cls is not None:
        assert typ is not None
        return await api.search_category([(cls, typ)], near_query=query, **details)

    return await api.search(query, **details)


async def search_endpoint(api: NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /search endpoint. See API docs for details.
    """
    fmt = parse_format(params, SearchResults, 'jsonv2')
    debug = setup_debugging(params)
    details = parse_geometry_details(params, fmt)

    details['countries']  = params.get('countrycodes', None)
    details['excluded'] = params.get('exclude_place_ids', None)
    details['viewbox'] = params.get('viewbox', None) or params.get('viewboxlbrt', None)
    details['bounded_viewbox'] = params.get_bool('bounded', False)
    details['dedupe'] = params.get_bool('dedupe', True)

    max_results = max(1, min(50, params.get_int('limit', 10)))
    details['max_results'] = max_results + min(10, max_results) \
                             if details['dedupe'] else max_results

    details['min_rank'], details['max_rank'] = \
        helpers.feature_type_to_rank(params.get('featureType', ''))
    if params.get('featureType', None) is not None:
        details['layers'] = DataLayer.ADDRESS
    else:
        details['layers'] = get_layers(params)

    details['locales'] = Locales.from_accept_languages(get_accepted_languages(params))

    # unstructured query parameters
    query = params.get('q', None)
    # structured query parameters
    queryparts = {}
    for key in ('amenity', 'street', 'city', 'county', 'state', 'postalcode', 'country'):
        details[key] = params.get(key, None)
        if details[key]:
            queryparts[key] = details[key]

    try:
        if query is not None:
            if queryparts:
                params.raise_error("Structured query parameters"
                                   "(amenity, street, city, county, state, postalcode, country)"
                                   " cannot be used together with 'q' parameter.")
            queryparts['q'] = query
            results = await _unstructured_search(query, api, details)
        else:
            query = ', '.join(queryparts.values())

            results = await api.search_address(**details)
    except UsageError as err:
        params.raise_error(str(err))

    if details['dedupe'] and len(results) > 1:
        results = helpers.deduplicate_results(results, max_results)

    if debug:
        return build_response(params, loglib.get_and_disable(), num_results=len(results))

    if fmt == 'xml':
        helpers.extend_query_parts(queryparts, details,
                                   params.get('featureType', ''),
                                   params.get_bool('namedetails', False),
                                   params.get_bool('extratags', False),
                                   (str(r.place_id) for r in results if r.place_id))
        queryparts['format'] = fmt

        moreurl = params.base_uri() + '/search?' + urlencode(queryparts)
    else:
        moreurl = ''

    fmt_options = {'query': query, 'more_url': moreurl,
                   'exclude_place_ids': queryparts.get('exclude_place_ids'),
                   'viewbox': queryparts.get('viewbox'),
                   'extratags': params.get_bool('extratags', False),
                   'namedetails': params.get_bool('namedetails', False),
                   'addressdetails': params.get_bool('addressdetails', False)}

    output = formatting.format_result(results, fmt, fmt_options)

    return build_response(params, output, num_results=len(results))


async def deletable_endpoint(api: NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /deletable endpoint.
        This is a special endpoint that shows polygons that have been
        deleted or are broken in the OSM data but are kept in the
        Nominatim database to minimize disruption.
    """
    fmt = parse_format(params, RawDataList, 'json')

    async with api.begin() as conn:
        sql = sa.text(""" SELECT p.place_id, country_code,
                                 name->'name' as name, i.*
                          FROM placex p, import_polygon_delete i
                          WHERE p.osm_id = i.osm_id AND p.osm_type = i.osm_type
                                AND p.class = i.class AND p.type = i.type
                      """)
        results = RawDataList(r._asdict() for r in await conn.execute(sql))

    return build_response(params, formatting.format_result(results, fmt, {}))


async def polygons_endpoint(api: NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /polygons endpoint.
        This is a special endpoint that shows polygons that have changed
        their size but are kept in the Nominatim database with their
        old area to minimize disruption.
    """
    fmt = parse_format(params, RawDataList, 'json')
    sql_params: Dict[str, Any] = {
        'days': params.get_int('days', -1),
        'cls': params.get('class')
    }
    reduced = params.get_bool('reduced', False)

    async with api.begin() as conn:
        sql = sa.select(sa.text("""osm_type, osm_id, class, type,
                                   name->'name' as name,
                                   country_code, errormessage, updated"""))\
                .select_from(sa.text('import_polygon_error'))
        if sql_params['days'] > 0:
            sql = sql.where(sa.text("updated > 'now'::timestamp - make_interval(days => :days)"))
        if reduced:
            sql = sql.where(sa.text("errormessage like 'Area reduced%'"))
        if sql_params['cls'] is not None:
            sql = sql.where(sa.text("class = :cls"))

        sql = sql.order_by(sa.literal_column('updated').desc()).limit(1000)

        results = RawDataList(r._asdict() for r in await conn.execute(sql, sql_params))

    return build_response(params, formatting.format_result(results, fmt, {}))


EndpointFunc = Callable[[NominatimAPIAsync, ASGIAdaptor], Any]

ROUTES = [
    ('status', status_endpoint),
    ('details', details_endpoint),
    ('reverse', reverse_endpoint),
    ('lookup', lookup_endpoint),
    ('search', search_endpoint),
    ('deletable', deletable_endpoint),
    ('polygons', polygons_endpoint),
]
