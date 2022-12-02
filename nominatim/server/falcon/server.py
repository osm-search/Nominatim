# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Server implementation using the falcon webserver framework.
"""
from pathlib import Path

import falcon.asgi

from nominatim.api import NominatimAPIAsync
from nominatim.apicmd.status import StatusResult
import nominatim.result_formatter.v1 as formatting

CONTENT_TYPE = {
  'text': falcon.MEDIA_TEXT,
  'xml': falcon.MEDIA_XML
}

class NominatimV1:

    def __init__(self, project_dir: Path):
        self.api = NominatimAPIAsync(project_dir)
        self.formatters = {}

        for rtype in (StatusResult, ):
            self.formatters[rtype] = formatting.create(rtype)

    def parse_format(self, req, rtype, default):
        req.context.format = req.get_param('format', default=default)
        req.context.formatter = self.formatters[rtype]

        if not req.context.formatter.supports_format(req.context.format):
            raise falcon.HTTPBadRequest(
                description="Parameter 'format' must be one of: " +
                            ', '.join(req.context.formatter.list_formats()))


    def format_response(self, req, resp, result):
        resp.text = req.context.formatter.format(result, req.context.format)
        resp.content_type = CONTENT_TYPE.get(req.context.format, falcon.MEDIA_JSON)


    async def on_get_status(self, req, resp):
        self.parse_format(req, StatusResult, 'text')

        result = await self.api.status()

        self.format_response(req, resp, result)


def get_application(project_dir: Path) -> falcon.asgi.App:
    app = falcon.asgi.App()

    api = NominatimV1(project_dir)

    app.add_route('/status', api, suffix='status')

    return app
