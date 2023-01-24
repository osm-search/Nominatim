# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the sanic webserver framework.
"""
from typing import Any, Optional, Mapping
from pathlib import Path

import sanic

from nominatim.api import NominatimAPIAsync, StatusResult
import nominatim.api.v1 as api_impl

api = sanic.Blueprint('NominatimAPI')

CONTENT_TYPE = {
  'text': 'text/plain; charset=utf-8',
  'xml': 'text/xml; charset=utf-8'
}

def usage_error(msg: str) -> sanic.HTTPResponse:
    """ Format the response for an error with the query parameters.
    """
    return sanic.response.text(msg, status=400)


def api_response(request: sanic.Request, result: Any) -> sanic.HTTPResponse:
    """ Render a response from the query results using the configured
        formatter.
    """
    body = api_impl.format_result(result, request.ctx.format)
    return sanic.response.text(body,
                               content_type=CONTENT_TYPE.get(request.ctx.format,
                                                             'application/json'))


@api.on_request # type: ignore[misc]
async def extract_format(request: sanic.Request) -> Optional[sanic.HTTPResponse]:
    """ Get and check the 'format' parameter and prepare the formatter.
        `ctx.result_type` describes the expected return type and
        `ctx.default_format` the format value to assume when no parameter
        is present.
    """
    assert request.route is not None

    request.ctx.format = request.args.get('format', request.route.ctx.default_format)
    if not api_impl.supports_format(request.route.ctx.result_type, request.ctx.format):
        return usage_error("Parameter 'format' must be one of: " +
                           ', '.join(api_impl.list_formats(request.route.ctx.result_type)))

    return None


@api.get('/status', ctx_result_type=StatusResult, ctx_default_format='text')
async def status(request: sanic.Request) -> sanic.HTTPResponse:
    """ Implementation of status endpoint.
    """
    result = await request.app.ctx.api.status()
    response = api_response(request, result)

    if request.ctx.format == 'text' and result.status:
        response.status = 500

    return response


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> sanic.Sanic:
    """ Create a Nominatim sanic ASGI application.
    """
    app = sanic.Sanic("NominatimInstance")

    app.ctx.api = NominatimAPIAsync(project_dir, environ)

    app.blueprint(api)

    return app
