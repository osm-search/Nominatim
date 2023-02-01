# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper fixtures for API call tests.
"""
from pathlib import Path
import pytest
import time

import nominatim.api as napi

class APITester:

    def __init__(self):
        self.api = napi.NominatimAPI(Path('/invalid'), {})
        self.async_to_sync(self.api._async_api.setup_database())


    def async_to_sync(self, func):
        """ Run an asynchronous function until completion using the
            internal loop of the API.
        """
        return self.api._loop.run_until_complete(func)


    def add_data(self, table, data):
        """ Insert data into the given table.
        """
        sql = getattr(self.api._async_api._tables, table).insert()
        self.async_to_sync(self.exec_async(sql, data))


    async def exec_async(self, sql, *args, **kwargs):
        async with self.api._async_api.begin() as conn:
            return await conn.execute(sql, *args, **kwargs)


    async def create_tables(self):
        async with self.api._async_api._engine.begin() as conn:
            await conn.run_sync(self.api._async_api._tables.meta.create_all)


@pytest.fixture
def apiobj(temp_db_with_extensions):
    """ Create an asynchronous SQLAlchemy engine for the test DB.
    """
    testapi = APITester()
    testapi.async_to_sync(testapi.create_tables())
    yield testapi
    testapi.api.close()
