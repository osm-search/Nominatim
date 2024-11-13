# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the falcon webserver framework.
"""
from typing import Optional, Mapping, Any, List
from pathlib import Path
import datetime as dt
import asyncio

from falcon.asgi import App, Request, Response

from ...config import Configuration
from ...core import NominatimAPIAsync
from ... import v1 as api_impl
from ...result_formatting import FormatDispatcher, load_format_dispatcher
from ... import logging as loglib
from ..asgi_adaptor import ASGIAdaptor, EndpointFunc


class HTTPNominatimError(Exception):
    """ A special exception class for errors raised during processing.
    """
    def __init__(self, msg: str, status: int, content_type: str) -> None:
        self.msg = msg
        self.status = status
        self.content_type = content_type


async def nominatim_error_handler(req: Request, resp: Response,
                                  exception: HTTPNominatimError,
                                  _: Any) -> None:
    """ Special error handler that passes message and content type as
        per exception info.
    """
    resp.status = exception.status
    resp.text = exception.msg
    resp.content_type = exception.content_type


async def timeout_error_handler(req: Request, resp: Response,
                                exception: TimeoutError,
                                _: Any) -> None:
    """ Special error handler that passes message and content type as
        per exception info.
    """
    resp.status = 503

    loglib.log().comment('Aborted: Query took too long to process.')
    logdata = loglib.get_and_disable()
    if logdata:
        resp.text = logdata
        resp.content_type = 'text/html; charset=utf-8'
    else:
        resp.text = "Query took too long to process."
        resp.content_type = 'text/plain; charset=utf-8'


class ParamWrapper(ASGIAdaptor):
    """ Adaptor class for server glue to Falcon framework.
    """

    def __init__(self, req: Request, resp: Response,
                 config: Configuration, formatter: FormatDispatcher) -> None:
        self.request = req
        self.response = resp
        self._config = config
        self._formatter = formatter

    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.request.get_param(name, default=default)

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return self.request.get_header(name, default=default)

    def error(self, msg: str, status: int = 400) -> HTTPNominatimError:
        return HTTPNominatimError(msg, status, self.content_type)

    def create_response(self, status: int, output: str, num_results: int) -> None:
        self.response.context.num_results = num_results
        self.response.status = status
        self.response.text = output
        self.response.content_type = self.content_type

    def base_uri(self) -> str:
        return self.request.forwarded_prefix

    def config(self) -> Configuration:
        return self._config

    def formatting(self) -> FormatDispatcher:
        return self._formatter


class EndpointWrapper:
    """ Converter for server glue endpoint functions to Falcon request handlers.
    """

    def __init__(self, name: str, func: EndpointFunc, api: NominatimAPIAsync,
                 formatter: FormatDispatcher) -> None:
        self.name = name
        self.func = func
        self.api = api
        self.formatter = formatter

    async def on_get(self, req: Request, resp: Response) -> None:
        """ Implementation of the endpoint.
        """
        await self.func(self.api, ParamWrapper(req, resp, self.api.config,
                                               self.formatter))


class FileLoggingMiddleware:
    """ Middleware to log selected requests into a file.
    """

    def __init__(self, file_name: str):
        self.fd = open(file_name, 'a', buffering=1, encoding='utf8')

    async def process_request(self, req: Request, _: Response) -> None:
        """ Callback before the request starts timing.
        """
        req.context.start = dt.datetime.now(tz=dt.timezone.utc)

    async def process_response(self, req: Request, resp: Response,
                               resource: Optional[EndpointWrapper],
                               req_succeeded: bool) -> None:
        """ Callback after requests writes to the logfile. It only
            writes logs for successful requests for search, reverse and lookup.
        """
        if not req_succeeded or resource is None or resp.status != 200\
           or resource.name not in ('reverse', 'search', 'lookup', 'details'):
            return

        finish = dt.datetime.now(tz=dt.timezone.utc)
        duration = (finish - req.context.start).total_seconds()
        params = req.scope['query_string'].decode('utf8')
        start = req.context.start.replace(tzinfo=None)\
                                 .isoformat(sep=' ', timespec='milliseconds')

        self.fd.write(f"[{start}] "
                      f"{duration:.4f} {getattr(resp.context, 'num_results', 0)} "
                      f'{resource.name} "{params}"\n')


class APIMiddleware:
    """ Middleware managing the Nominatim database connection.
    """

    def __init__(self, project_dir: Path, environ: Optional[Mapping[str, str]]) -> None:
        self.api = NominatimAPIAsync(project_dir, environ)
        self.app: Optional[App] = None

    @property
    def config(self) -> Configuration:
        """ Get the configuration for Nominatim.
        """
        return self.api.config

    def set_app(self, app: App) -> None:
        """ Set the Falcon application this middleware is connected to.
        """
        self.app = app

    async def process_startup(self, *_: Any) -> None:
        """ Process the ASGI lifespan startup event.
        """
        assert self.app is not None
        legacy_urls = self.api.config.get_bool('SERVE_LEGACY_URLS')
        formatter = load_format_dispatcher('v1', self.api.config.project_dir)
        for name, func in api_impl.ROUTES:
            endpoint = EndpointWrapper(name, func, self.api, formatter)
            self.app.add_route(f"/{name}", endpoint)
            if legacy_urls:
                self.app.add_route(f"/{name}.php", endpoint)

    async def process_shutdown(self, *_: Any) -> None:
        """Process the ASGI lifespan shutdown event.
        """
        await self.api.close()


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> App:
    """ Create a Nominatim Falcon ASGI application.
    """
    apimw = APIMiddleware(project_dir, environ)

    middleware: List[object] = [apimw]
    log_file = apimw.config.LOG_FILE
    if log_file:
        middleware.append(FileLoggingMiddleware(log_file))

    app = App(cors_enable=apimw.config.get_bool('CORS_NOACCESSCONTROL'),
              middleware=middleware)

    apimw.set_app(app)
    app.add_error_handler(HTTPNominatimError, nominatim_error_handler)
    app.add_error_handler(TimeoutError, timeout_error_handler)
    # different from TimeoutError in Python <= 3.10
    app.add_error_handler(asyncio.TimeoutError, timeout_error_handler)  # type: ignore[arg-type]

    return app


def run_wsgi() -> App:
    """ Entry point for uvicorn.

        Make sure uvicorn is run from the project directory.
    """
    return get_application(Path('.'))
