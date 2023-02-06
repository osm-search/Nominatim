# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the falcon webserver framework.
"""
from typing import Optional, Mapping, cast
from pathlib import Path

import falcon
from falcon.asgi import App, Request, Response

from nominatim.api import NominatimAPIAsync
import nominatim.api.v1 as api_impl
from nominatim.config import Configuration


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


    def error(self, msg: str, status: int = 400) -> falcon.HTTPError:
        if status == 400:
            return falcon.HTTPBadRequest(description=msg)
        if status == 404:
            return falcon.HTTPNotFound(description=msg)

        return falcon.HTTPError(status, description=msg)


    def create_response(self, status: int, output: str, content_type: str) -> None:
        self.response.status = status
        self.response.text = output
        self.response.content_type = content_type


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

    legacy_urls = api.config.get_bool('SERVE_LEGACY_URLS')
    for name, func in api_impl.ROUTES:
        endpoint = EndpointWrapper(func, api)
        app.add_route(f"/{name}", endpoint)
        if legacy_urls:
            app.add_route(f"/{name}.php", endpoint)

    return app
