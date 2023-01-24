# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the falcon webserver framework.
"""
from typing import Type, Any, Optional, Mapping
from pathlib import Path

import falcon
import falcon.asgi

from nominatim.api import NominatimAPIAsync, StatusResult
import nominatim.api.v1 as api_impl

CONTENT_TYPE = {
  'text': falcon.MEDIA_TEXT,
  'xml': falcon.MEDIA_XML
}

class NominatimV1:
    """ Implementation of V1 version of the Nominatim API.
    """

    def __init__(self, project_dir: Path, environ: Optional[Mapping[str, str]]) -> None:
        self.api = NominatimAPIAsync(project_dir, environ)


    def parse_format(self, req: falcon.asgi.Request, rtype: Type[Any], default: str) -> None:
        """ Get and check the 'format' parameter and prepare the formatter.
            `rtype` describes the expected return type and `default` the
            format value to assume when no parameter is present.
        """
        req.context.format = req.get_param('format', default=default)

        if not api_impl.supports_format(rtype, req.context.format):
            raise falcon.HTTPBadRequest(
                description="Parameter 'format' must be one of: " +
                            ', '.join(api_impl.list_formats(rtype)))


    def format_response(self, req: falcon.asgi.Request, resp: falcon.asgi.Response,
                        result: Any) -> None:
        """ Render response into a string according to the formatter
            set in `parse_format()`.
        """
        resp.text = api_impl.format_result(result, req.context.format)
        resp.content_type = CONTENT_TYPE.get(req.context.format, falcon.MEDIA_JSON)


    async def on_get_status(self, req: falcon.asgi.Request, resp: falcon.asgi.Response) -> None:
        """ Implementation of status endpoint.
        """
        self.parse_format(req, StatusResult, 'text')

        result = await self.api.status()

        self.format_response(req, resp, result)
        if result.status and req.context.format == 'text':
            resp.status = 500


def get_application(project_dir: Path,
                    environ: Optional[Mapping[str, str]] = None) -> falcon.asgi.App:
    """ Create a Nominatim falcon ASGI application.
    """
    app = falcon.asgi.App()

    api = NominatimV1(project_dir, environ)

    app.add_route('/status', api, suffix='status')

    return app
