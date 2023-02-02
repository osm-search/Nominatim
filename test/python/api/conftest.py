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
import datetime as dt

import nominatim.api as napi
from nominatim.db.sql_preprocessor import SQLPreprocessor

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


    def add_placex(self, **kw):
        name = kw.get('name')
        if isinstance(name, str):
            name = {'name': name}

        self.add_data('placex',
                     {'place_id': kw.get('place_id', 1000),
                      'osm_type': kw.get('osm_type', 'W'),
                      'osm_id': kw.get('osm_id', 4),
                      'class_': kw.get('class_', 'highway'),
                      'type': kw.get('type', 'residential'),
                      'name': name,
                      'address': kw.get('address'),
                      'extratags': kw.get('extratags'),
                      'parent_place_id': kw.get('parent_place_id'),
                      'linked_place_id': kw.get('linked_place_id'),
                      'admin_level': kw.get('admin_level', 15),
                      'country_code': kw.get('country_code'),
                      'housenumber': kw.get('housenumber'),
                      'postcode': kw.get('postcode'),
                      'wikipedia': kw.get('wikipedia'),
                      'rank_search': kw.get('rank_search', 30),
                      'rank_address': kw.get('rank_address', 30),
                      'importance': kw.get('importance'),
                      'centroid': 'SRID=4326;POINT(%f %f)' % kw.get('centroid', (23.0, 34.0)),
                      'indexed_date': kw.get('indexed_date',
                                             dt.datetime(2022, 12, 7, 14, 14, 46, 0)),
                      'geometry': 'SRID=4326;' + kw.get('geometry', 'POINT(23 34)')})


    def add_address_placex(self, object_id, **kw):
        self.add_placex(**kw)
        self.add_data('addressline',
                      {'place_id': object_id,
                       'address_place_id': kw.get('place_id', 1000),
                       'distance': kw.get('distance', 0.0),
                       'cached_rank_address': kw.get('rank_address', 30),
                       'fromarea': kw.get('fromarea', False),
                       'isaddress': kw.get('isaddress', True)})


    def add_osmline(self, **kw):
        self.add_data('osmline',
                     {'place_id': kw.get('place_id', 10000),
                      'osm_id': kw.get('osm_id', 4004),
                      'parent_place_id': kw.get('parent_place_id'),
                      'indexed_date': kw.get('indexed_date',
                                             dt.datetime(2022, 12, 7, 14, 14, 46, 0)),
                      'startnumber': kw.get('startnumber', 2),
                      'endnumber': kw.get('endnumber', 6),
                      'step': kw.get('step', 2),
                      'address': kw.get('address'),
                      'postcode': kw.get('postcode'),
                      'country_code': kw.get('country_code'),
                      'linegeo': 'SRID=4326;' + kw.get('geometry', 'LINESTRING(1.1 -0.2, 1.09 -0.22)')})


    async def exec_async(self, sql, *args, **kwargs):
        async with self.api._async_api.begin() as conn:
            return await conn.execute(sql, *args, **kwargs)


    async def create_tables(self):
        async with self.api._async_api._engine.begin() as conn:
            await conn.run_sync(self.api._async_api._tables.meta.create_all)


@pytest.fixture
def apiobj(temp_db_with_extensions, temp_db_conn):
    """ Create an asynchronous SQLAlchemy engine for the test DB.
    """
    testapi = APITester()
    testapi.async_to_sync(testapi.create_tables())

    SQLPreprocessor(temp_db_conn, testapi.api.config)\
        .run_sql_file(temp_db_conn, 'functions/address_lookup.sql')

    yield testapi

    testapi.api.close()
