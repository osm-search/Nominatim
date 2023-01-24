# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the sanic webserver framework.
"""
from typing import Any, Optional, Mapping, Callable, cast, Coroutine
from pathlib import Path

from sanic import Request, HTTPResponse, Sanic
from sanic.exceptions import SanicException
from sanic.response import text as TextResponse

from nominatim.api import NominatimAPIAsync
import nominatim.api.v1 as api_impl

class ParamWrapper(api_impl.ASGIAdaptor):
    """ Adaptor class for server glue to Sanic framework.
    """

    def __init__(self, request: Request) -> None:
        self.request = request


    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return cast(Optional[str], self.request.args.get(name, default))


    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return cast(Optional[str], self.request.headers.get(name, default))


    def error(self, msg: str) -> SanicException:
        return SanicException(msg, status_code=400)


    def create_response(self, status: int, output: str,
                        content_type: str) -> HTTPResponse:
        return TextResponse(output, status=status, content_type=content_type)


def _wrap_endpoint(func: api_impl.EndpointFunc)\
       -> Callable[[Request], Coroutine[Any, Any, HTTPResponse]]:
    async def _callback(request: Request) -> HTTPResponse:
        return cast(HTTPResponse, await func(request.app.ctx.api, ParamWrapper(request)))

    return _callback


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> Sanic:
    """ Create a Nominatim sanic ASGI application.
    """
    app = Sanic("NominatimInstance")

    app.ctx.api = NominatimAPIAsync(project_dir, environ)

    for name, func in api_impl.ROUTES:
        app.add_route(_wrap_endpoint(func), f"/{name}", name=f"v1_{name}_simple")

    return app
