# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Generic part of the server implementation of the v1 API.
Combine with the scaffolding provided for the various Python ASGI frameworks.
"""
from typing import Optional, Any, Type, Callable
import abc

from nominatim.config import Configuration
import nominatim.api as napi
import nominatim.api.logging as loglib
from nominatim.api.v1.format import dispatch as formatting

CONTENT_TYPE = {
  'text': 'text/plain; charset=utf-8',
  'xml': 'text/xml; charset=utf-8',
  'jsonp': 'application/javascript',
  'debug': 'text/html; charset=utf-8'
}


class ASGIAdaptor(abc.ABC):
    """ Adapter class for the different ASGI frameworks.
        Wraps functionality over concrete requests and responses.
    """

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
    def create_response(self, status: int, output: str, content_type: str) -> Any:
        """ Create a response from the given parameters. The result will
            be returned by the endpoint functions. The adaptor may also
            return None when the response is created internally with some
            different means.

            The response must return the HTTP given status code 'status', set
            the HTTP content-type headers to the string provided and the
            body of the response to 'output'.
        """


    @abc.abstractmethod
    def config(self) -> Configuration:
        """ Return the current configuration object.
        """


    def build_response(self, output: str, media_type: str, status: int = 200) -> Any:
        """ Create a response from the given output. Wraps a JSONP function
            around the response, if necessary.
        """
        if media_type == 'json' and status == 200:
            jsonp = self.get('json_callback')
            if jsonp is not None:
                if any(not part.isidentifier() for part in jsonp.split('.')):
                    raise self.error('Invalid json_callback value')
                output = f"{jsonp}({output})"
                media_type = 'jsonp'

        return self.create_response(status, output,
                                    CONTENT_TYPE.get(media_type, 'application/json'))


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

            raise self.error(f"Parameter '{name}' missing.")

        try:
            return int(value)
        except ValueError as exc:
            raise self.error(f"Parameter '{name}' must be a number.") from exc


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

            raise self.error(f"Parameter '{name}' missing.")

        return value != '0'


    def get_accepted_languages(self) -> str:
        """ Return the accepted langauges.
        """
        return self.get('accept-language')\
               or self.get_header('http_accept_language')\
               or self.config().DEFAULT_LANGUAGE


    def setup_debugging(self) -> bool:
        """ Set up collection of debug information if requested.

            Return True when debugging was requested.
        """
        if self.get_bool('debug', False):
            loglib.set_log_output('html')
            return True

        return False


def parse_format(params: ASGIAdaptor, result_type: Type[Any], default: str) -> str:
    """ Get and check the 'format' parameter and prepare the formatter.
        `fmtter` is a formatter and `default` the
        format value to assume when no parameter is present.
    """
    fmt = params.get('format', default=default)
    assert fmt is not None

    if not formatting.supports_format(result_type, fmt):
        raise params.error("Parameter 'format' must be one of: " +
                           ', '.join(formatting.list_formats(result_type)))

    return fmt


async def status_endpoint(api: napi.NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /status endpoint. See API docs for details.
    """
    result = await api.status()

    fmt = parse_format(params, napi.StatusResult, 'text')

    if fmt == 'text' and result.status:
        status_code = 500
    else:
        status_code = 200

    return params.build_response(formatting.format_result(result, fmt, {}), fmt,
                                 status=status_code)


async def details_endpoint(api: napi.NominatimAPIAsync, params: ASGIAdaptor) -> Any:
    """ Server glue for /details endpoint. See API docs for details.
    """
    place_id = params.get_int('place_id', 0)
    place: napi.PlaceRef
    if place_id:
        place = napi.PlaceID(place_id)
    else:
        osmtype = params.get('osmtype')
        if osmtype is None:
            raise params.error("Missing ID parameter 'place_id' or 'osmtype'.")
        place = napi.OsmID(osmtype, params.get_int('osmid'), params.get('class'))

    debug = params.setup_debugging()

    details = napi.LookupDetails(address_details=params.get_bool('addressdetails', False),
                                 linked_places=params.get_bool('linkedplaces', False),
                                 parented_places=params.get_bool('hierarchy', False),
                                 keywords=params.get_bool('keywords', False))

    if params.get_bool('polygon_geojson', False):
        details.geometry_output = napi.GeometryFormat.GEOJSON

    locales = napi.Locales.from_accept_languages(params.get_accepted_languages())

    result = await api.lookup(place, details)

    if debug:
        return params.build_response(loglib.get_and_disable(), 'debug')

    if result is None:
        raise params.error('No place with that OSM ID found.', status=404)

    output = formatting.format_result(
                 result,
                 'details-json',
                 {'locales': locales,
                  'group_hierarchy': params.get_bool('group_hierarchy', False),
                  'icon_base_url': params.config().MAPICON_URL})

    return params.build_response(output, 'json')


EndpointFunc = Callable[[napi.NominatimAPIAsync, ASGIAdaptor], Any]

ROUTES = [
    ('status', status_endpoint),
    ('details', details_endpoint)
]
