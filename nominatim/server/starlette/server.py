# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the starlette webserver framework.
"""
from typing import Any, Optional, Mapping, Callable, cast, Coroutine
from pathlib import Path

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from nominatim.config import Configuration
from nominatim.api import NominatimAPIAsync
import nominatim.api.v1 as api_impl

class ParamWrapper(api_impl.ASGIAdaptor):
    """ Adaptor class for server glue to Starlette framework.
    """

    def __init__(self, request: Request) -> None:
        self.request = request


    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.request.query_params.get(name, default=default)


    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.request.headers.get(name, default)


    def error(self, msg: str) -> HTTPException:
        return HTTPException(400, detail=msg)


    def create_response(self, status: int, output: str, content_type: str) -> Response:
        return Response(output, status_code=status, media_type=content_type)


def _wrap_endpoint(func: api_impl.EndpointFunc)\
        -> Callable[[Request], Coroutine[Any, Any, Response]]:
    async def _callback(request: Request) -> Response:
        return cast(Response, await func(request.app.state.API, ParamWrapper(request)))

    return _callback


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> Starlette:
    """ Create a Nominatim falcon ASGI application.
    """
    config = Configuration(project_dir, environ)

    routes = []
    legacy_urls = config.get_bool('SERVE_LEGACY_URLS')
    for name, func in api_impl.ROUTES:
        endpoint = _wrap_endpoint(func)
        routes.append(Route(f"/{name}", endpoint=endpoint))
        if legacy_urls:
            routes.append(Route(f"/{name}.php", endpoint=endpoint))

    middleware = []
    if config.get_bool('CORS_NOACCESSCONTROL'):
        middleware.append(Middleware(CORSMiddleware, allow_origins=['*']))

    app = Starlette(debug=True, routes=routes, middleware=middleware)

    app.state.API = NominatimAPIAsync(project_dir, environ)

    return app
