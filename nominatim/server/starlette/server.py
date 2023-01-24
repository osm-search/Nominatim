# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the starlette webserver framework.
"""
from typing import Any, Type, Optional, Mapping
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.requests import Request

from nominatim.api import NominatimAPIAsync, StatusResult
import nominatim.result_formatter.v1 as formatting

CONTENT_TYPE = {
  'text': 'text/plain; charset=utf-8',
  'xml': 'text/xml; charset=utf-8'
}

FORMATTERS = {
    StatusResult: formatting.create(StatusResult)
}


def parse_format(request: Request, rtype: Type[Any], default: str) -> None:
    """ Get and check the 'format' parameter and prepare the formatter.
        `rtype` describes the expected return type and `default` the
        format value to assume when no parameter is present.
    """
    fmt = request.query_params.get('format', default=default)
    fmtter = FORMATTERS[rtype]

    if not fmtter.supports_format(fmt):
        raise HTTPException(400, detail="Parameter 'format' must be one of: " +
                                        ', '.join(fmtter.list_formats()))

    request.state.format = fmt
    request.state.formatter = fmtter


def format_response(request: Request, result: Any) -> Response:
    """ Render response into a string according to the formatter
        set in `parse_format()`.
    """
    fmt = request.state.format
    return Response(request.state.formatter.format(result, fmt),
                    media_type=CONTENT_TYPE.get(fmt, 'application/json'))


async def on_status(request: Request) -> Response:
    """ Implementation of status endpoint.
    """
    parse_format(request, StatusResult, 'text')
    result = await request.app.state.API.status()
    response = format_response(request, result)

    if request.state.format == 'text' and result.status:
        response.status_code = 500

    return response


V1_ROUTES = [
    Route('/status', endpoint=on_status)
]

def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> Starlette:
    """ Create a Nominatim falcon ASGI application.
    """
    app = Starlette(debug=True, routes=V1_ROUTES)

    app.state.API = NominatimAPIAsync(project_dir, environ)

    return app
