# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Various helper classes for running Nominatim commands.
"""
import asyncio
from collections import namedtuple

APIResponse = namedtuple('APIResponse', ['endpoint', 'status', 'body', 'headers'])


class APIRunner:
    """ Execute a call to an API endpoint.
    """
    def __init__(self, environ, api_engine):
        create_func = getattr(self, f"create_engine_{api_engine}")
        self.exec_engine = create_func(environ)

    def run(self, endpoint, params, http_headers):
        return asyncio.run(self.exec_engine(endpoint, params, http_headers))

    def run_step(self, endpoint, base_params, datatable, fmt, http_headers):
        if fmt:
            base_params['format'] = fmt.strip()

        if datatable:
            if datatable[0] == ['param', 'value']:
                base_params.update(datatable[1:])
            else:
                base_params.update(zip(datatable[0], datatable[1]))

        return self.run(endpoint, base_params, http_headers)

    def create_engine_falcon(self, environ):
        import nominatim_api.server.falcon.server
        import falcon.testing

        async def exec_engine_falcon(endpoint, params, http_headers):
            app = nominatim_api.server.falcon.server.get_application(None, environ)

            async with falcon.testing.ASGIConductor(app) as conductor:
                response = await conductor.get("/" + endpoint, params=params,
                                               headers=http_headers)

            return APIResponse(endpoint, response.status_code,
                               response.text, response.headers)

        return exec_engine_falcon

    def create_engine_starlette(self, environ):
        import nominatim_api.server.starlette.server
        from asgi_lifespan import LifespanManager
        from starlette.testclient import TestClient

        async def _request(endpoint, params, http_headers):
            app = nominatim_api.server.starlette.server.get_application(None, environ)

            async with LifespanManager(app):
                client = TestClient(app, base_url="http://nominatim.test")
                response = client.get("/" + endpoint, params=params, headers=http_headers)

            return APIResponse(endpoint, response.status_code,
                               response.text, response.headers)

        return _request
