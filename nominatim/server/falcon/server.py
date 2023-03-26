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


    def create_response(self, status: int, output: str) -> None:
        self.response.status = status
        self.response.text = output
        self.response.content_type = self.content_type


    def config(self) -> Configuration:
        return self._config


class EndpointWrapper:
    """ Converter for server glue endpoint functions to Falcon request handlers.
    """

    def __init__(self, func: api_impl.EndpointFunc, api: NominatimAPIAsync) -> None:
        self.func = func
        self.api = api


    async def on_get(self, req: Request, resp: Response) -> None:
        """ Implementation of the endpoint.
        """
        await self.func(self.api, ParamWrapper(req, resp, self.api.config))


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> App:
    """ Create a Nominatim Falcon ASGI application.
    """
    api = NominatimAPIAsync(project_dir, environ)

    app = App(cors_enable=api.config.get_bool('CORS_NOACCESSCONTROL'))
    app.add_error_handler(HTTPNominatimError, nominatim_error_handler)

    legacy_urls = api.config.get_bool('SERVE_LEGACY_URLS')
    for name, func in api_impl.ROUTES:
        endpoint = EndpointWrapper(func, api)
        app.add_route(f"/{name}", endpoint)
        if legacy_urls:
            app.add_route(f"/{name}.php", endpoint)

    return app
