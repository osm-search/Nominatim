# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the starlette webserver framework.
"""
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.responses import Response

from nominatim.api import NominatimAPIAsync
from nominatim.apicmd.status import StatusResult
import nominatim.result_formatter.v1 as formatting

CONTENT_TYPE = {
  'text': 'text/plain; charset=utf-8',
  'xml': 'text/xml; charset=utf-8'
}

FORMATTERS = {
    StatusResult: formatting.create(StatusResult)
}


def parse_format(request, rtype, default):
    fmt = request.query_params.get('format', default=default)
    fmtter = FORMATTERS[rtype]

    if not fmtter.supports_format(fmt):
        raise HTTPException(400, detail="Parameter 'format' must be one of: " +
                                        ', '.join(fmtter.list_formats()))

    request.state.format = fmt
    request.state.formatter = fmtter


def format_response(request, result):
    fmt = request.state.format
    return Response(request.state.formatter.format(result, fmt),
                    media_type=CONTENT_TYPE.get(fmt, 'application/json'))


async def on_status(request):
    parse_format(request, StatusResult, 'text')
    result = await request.app.state.API.status()
    return format_response(request, result)


V1_ROUTES = [
    Route('/status', endpoint=on_status)
]

def get_application(project_dir: Path) -> Starlette:
    app = Starlette(debug=True, routes=V1_ROUTES)

    app.state.API = NominatimAPIAsync(project_dir)

    return app
