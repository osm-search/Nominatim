# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the starlette webserver framework.
"""
from typing import Any, Optional, Mapping, Callable, cast, Coroutine, Dict, \
                   Awaitable, AsyncIterator
from pathlib import Path
import asyncio
import contextlib
import datetime as dt

from starlette.applications import Starlette
from starlette.routing import Route
from starlette.exceptions import HTTPException
from starlette.responses import Response, PlainTextResponse, HTMLResponse
from starlette.requests import Request
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.middleware.cors import CORSMiddleware

from ...config import Configuration
from ...core import NominatimAPIAsync
from ...types import QueryStatistics
from ... import v1 as api_impl
from ...result_formatting import FormatDispatcher, load_format_dispatcher
from ..asgi_adaptor import ASGIAdaptor, EndpointFunc
from ... import logging as loglib


class ParamWrapper(ASGIAdaptor):
    """ Adaptor class for server glue to Starlette framework.
    """

    def __init__(self, request: Request) -> None:
        self.request = request

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.request.query_params.get(name, default=default)

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.request.headers.get(name, default)

    def error(self, msg: str, status: int = 400) -> HTTPException:
        return HTTPException(status, detail=msg,
                             headers={'content-type': self.content_type})

    def create_response(self, status: int, output: str, num_results: int) -> Response:
        setattr(self.request.state, 'num_results', num_results)
        return Response(output, status_code=status, media_type=self.content_type)

    def base_uri(self) -> str:
        scheme = self.request.url.scheme
        host = self.request.url.hostname
        port = self.request.url.port
        root = self.request.scope['root_path']
        if (scheme == 'http' and port == 80) or (scheme == 'https' and port == 443):
            port = None
        if port is not None:
            return f"{scheme}://{host}:{port}{root}"

        return f"{scheme}://{host}{root}"

    def config(self) -> Configuration:
        return cast(Configuration, self.request.app.state.API.config)

    def formatting(self) -> FormatDispatcher:
        return cast(FormatDispatcher, self.request.app.state.formatter)

    def query_stats(self) -> Optional[QueryStatistics]:
        return cast(Optional[QueryStatistics], getattr(self.request.state, 'query_stats', None))


def _wrap_endpoint(func: EndpointFunc)\
        -> Callable[[Request], Coroutine[Any, Any, Response]]:
    async def _callback(request: Request) -> Response:
        return cast(Response, await func(request.app.state.API, ParamWrapper(request)))

    return _callback


class FileLoggingMiddleware(BaseHTTPMiddleware):
    """ Middleware to log selected requests into a file.
    """

    def __init__(self, app: Starlette, file_name: str = '', logstr: str = ''):
        super().__init__(app)
        self.fd = open(file_name, 'a', buffering=1, encoding='utf8')
        self.logstr = logstr + '\n'

    async def dispatch(self, request: Request,
                       call_next: RequestResponseEndpoint) -> Response:
        qs = QueryStatistics()
        setattr(request.state, 'query_stats', qs)
        response = await call_next(request)

        if response.status_code != 200 or 'start' not in qs:
            return response

        for endpoint in ('reverse', 'search', 'lookup', 'details'):
            if request.url.path.startswith('/' + endpoint):
                qs['endpoint'] = endpoint
                break
        else:
            return response

        qs['query_string'] = request.scope['query_string'].decode('utf8')
        qs['results_total'] = getattr(request.state, 'num_results', 0)
        for param in ('start', 'end', 'start_query'):
            if isinstance(qs.get(param), dt.datetime):
                qs[param] = qs[param].replace(tzinfo=None)\
                                     .isoformat(sep=' ', timespec='milliseconds')

        self.fd.write(self.logstr.format_map(qs))

        return response


async def timeout_error(request: Request,
                        _: Exception) -> Response:
    """ Error handler for query timeouts.
    """
    loglib.log().comment('Aborted: Query took too long to process.')
    logdata = loglib.get_and_disable()

    if logdata:
        return HTMLResponse(logdata)

    return PlainTextResponse("Query took too long to process.", status_code=503)


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None,
                    debug: bool = True) -> Starlette:
    """ Create a Nominatim falcon ASGI application.
    """
    config = Configuration(project_dir, environ)

    middleware = []
    if config.get_bool('CORS_NOACCESSCONTROL'):
        middleware.append(Middleware(CORSMiddleware,
                                     allow_origins=['*'],
                                     allow_methods=['GET', 'OPTIONS'],
                                     max_age=86400))

    log_file = config.LOG_FILE
    if log_file:
        middleware.append(Middleware(FileLoggingMiddleware, file_name=log_file,  # type: ignore
                                     logstr=config.LOG_FORMAT))

    exceptions: Dict[Any, Callable[[Request, Exception], Awaitable[Response]]] = {
        TimeoutError: timeout_error,
        asyncio.TimeoutError: timeout_error
    }

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette) -> AsyncIterator[Any]:
        app.state.API = NominatimAPIAsync(project_dir, environ)
        config = app.state.API.config

        legacy_urls = config.get_bool('SERVE_LEGACY_URLS')
        for name, func in await api_impl.get_routes(app.state.API):
            endpoint = _wrap_endpoint(func)
            app.routes.append(Route(f"/{name}", endpoint=endpoint))
            if legacy_urls:
                app.routes.append(Route(f"/{name}.php", endpoint=endpoint))

        yield

        await app.state.API.close()

    app = Starlette(debug=debug, middleware=middleware,
                    exception_handlers=exceptions,
                    lifespan=lifespan)

    app.state.formatter = load_format_dispatcher('v1', project_dir)

    return app


def run_wsgi() -> Starlette:
    """ Entry point for uvicorn.
    """
    return get_application(Path('.'), debug=False)
