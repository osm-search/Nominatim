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


class ParamWrapper(api_impl.ASGIAdaptor):
    """ Adaptor class for server glue to Falcon framework.
    """

    def __init__(self, req: Request, resp: Response) -> None:
        self.request = req
        self.response = resp


    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return cast(Optional[str], self.request.get_param(name, default=default))


    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        return cast(Optional[str], self.request.get_header(name, default=default))


    def error(self, msg: str) -> falcon.HTTPBadRequest:
        return falcon.HTTPBadRequest(description=msg)


    def create_response(self, status: int, output: str, content_type: str) -> None:
        self.response.status = status
        self.response.text = output
        self.response.content_type = content_type


class EndpointWrapper:
    """ Converter for server glue endpoint functions to Falcon request handlers.
    """

    def __init__(self, func: api_impl.EndpointFunc, api: NominatimAPIAsync) -> None:
        self.func = func
        self.api = api


    async def on_get(self, req: Request, resp: Response) -> None:
        """ Implementation of the endpoint.
        """
        await self.func(self.api, ParamWrapper(req, resp))


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> App:
    """ Create a Nominatim Falcon ASGI application.
    """
    api = NominatimAPIAsync(project_dir, environ)

    app = App(cors_enable=api.config.get_bool('CORS_NOACCESSCONTROL'))
    for name, func in api_impl.ROUTES:
        app.add_route('/' + name, EndpointWrapper(func, api))

    return app
