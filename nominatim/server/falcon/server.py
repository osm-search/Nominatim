# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the falcon webserver framework.
"""
from typing import Optional, Mapping, cast, Any
from pathlib import Path
import datetime as dt

from falcon.asgi import App, Request, Response

from nominatim.api import NominatimAPIAsync
import nominatim.api.v1 as api_impl
from nominatim.config import Configuration

class HTTPNominatimError(Exception):
    """ A special exception class for errors raised during processing.
    """
    def __init__(self, msg: str, status: int, content_type: str) -> None:
        self.msg = msg
        self.status = status
        self.content_type = content_type


async def nominatim_error_handler(req: Request, resp: Response, #pylint: disable=unused-argument
                                  exception: HTTPNominatimError,
                                  _: Any) -> None:
    """ Special error handler that passes message and content type as
        per exception info.
    """
    resp.status = exception.status
    resp.text = exception.msg
    resp.content_type = exception.content_type


async def timeout_error_handler(req: Request, resp: Response, #pylint: disable=unused-argument
                                exception: TimeoutError, #pylint: disable=unused-argument
                                _: Any) -> None:
    """ Special error handler that passes message and content type as
        per exception info.
    """
    resp.status = 503
    resp.text = "Query took too long to process."
    resp.content_type = 'text/plain; charset=utf-8'


class ParamWrapper(api_impl.ASGIAdaptor):
    """ Adaptor class for server glue to Falcon framework.
    """

    def __init__(self, req: Request, resp: Response,
                 config: Configuration) -> None:
        self.request = req
        self.response = resp
        self._config = config


    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return cast(Optional[str], self.request.get_param(name, default=default))


    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return cast(Optional[str], self.request.get_header(name, default=default))


    def error(self, msg: str, status: int = 400) -> HTTPNominatimError:
        return HTTPNominatimError(msg, status, self.content_type)


    def create_response(self, status: int, output: str, num_results: int) -> None:
        self.response.context.num_results = num_results
        self.response.status = status
        self.response.text = output
        self.response.content_type = self.content_type


    def base_uri(self) -> str:
        return cast (str, self.request.forwarded_prefix)

    def config(self) -> Configuration:
        return self._config


class EndpointWrapper:
    """ Converter for server glue endpoint functions to Falcon request handlers.
    """

    def __init__(self, name: str, func: api_impl.EndpointFunc, api: NominatimAPIAsync) -> None:
        self.name = name
        self.func = func
        self.api = api


    async def on_get(self, req: Request, resp: Response) -> None:
        """ Implementation of the endpoint.
        """
        await self.func(self.api, ParamWrapper(req, resp, self.api.config))


class FileLoggingMiddleware:
    """ Middleware to log selected requests into a file.
    """

    def __init__(self, file_name: str):
        self.fd = open(file_name, 'a', buffering=1, encoding='utf8') # pylint: disable=R1732


    async def process_request(self, req: Request, _: Response) -> None:
        """ Callback before the request starts timing.
        """
        req.context.start = dt.datetime.now(tz=dt.timezone.utc)


    async def process_response(self, req: Request, resp: Response,
                               resource: Optional[EndpointWrapper],
                               req_succeeded: bool) -> None:
        """ Callback after requests writes to the logfile. It only
            writes logs for sucessful requests for search, reverse and lookup.
        """
        if not req_succeeded or resource is None or resp.status != 200\
            or resource.name not in ('reverse', 'search', 'lookup'):
            return

        finish = dt.datetime.now(tz=dt.timezone.utc)
        duration = (finish - req.context.start).total_seconds()
        params = req.scope['query_string'].decode('utf8')
        start = req.context.start.replace(tzinfo=None)\
                                 .isoformat(sep=' ', timespec='milliseconds')

        self.fd.write(f"[{start}] "
                      f"{duration:.4f} {getattr(resp.context, 'num_results', 0)} "
                      f'{resource.name} "{params}"\n')


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> App:
    """ Create a Nominatim Falcon ASGI application.
    """
    api = NominatimAPIAsync(project_dir, environ)

    middleware: Optional[object] = None
    log_file = api.config.LOG_FILE
    if log_file:
        middleware = FileLoggingMiddleware(log_file)

    app = App(cors_enable=api.config.get_bool('CORS_NOACCESSCONTROL'),
              middleware=middleware)
    app.add_error_handler(HTTPNominatimError, nominatim_error_handler)
    app.add_error_handler(TimeoutError, timeout_error_handler)

    legacy_urls = api.config.get_bool('SERVE_LEGACY_URLS')
    for name, func in api_impl.ROUTES:
        endpoint = EndpointWrapper(name, func, api)
        app.add_route(f"/{name}", endpoint)
        if legacy_urls:
            app.add_route(f"/{name}.php", endpoint)

    return app


def run_wsgi() -> App:
    """ Entry point for uvicorn.

        Make sure uvicorn is run from the project directory.
    """
    return get_application(Path('.'))
