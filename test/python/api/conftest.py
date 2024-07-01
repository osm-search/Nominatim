# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper fixtures for API call tests.
"""
from pathlib import Path
import pytest
import time
import datetime as dt

import sqlalchemy as sa

import nominatim_api as napi
from nominatim_db.db.sql_preprocessor import SQLPreprocessor
from nominatim_api.search.query_analyzer_factory import make_query_analyzer
from nominatim_db.tools import convert_sqlite
import nominatim_api.logging as loglib

class APITester:

    def __init__(self):
        self.api = napi.NominatimAPI(Path('/invalid'))
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

        centroid = kw.get('centroid', (23.0, 34.0))
        geometry = kw.get('geometry', 'POINT(%f %f)' % centroid)

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
                      'centroid': 'POINT(%f %f)' % centroid,
                      'indexed_status': kw.get('indexed_status', 0),
                      'indexed_date': kw.get('indexed_date',
                                             dt.datetime(2022, 12, 7, 14, 14, 46, 0)),
                      'geometry': geometry})


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
                      'linegeo': kw.get('geometry', 'LINESTRING(1.1 -0.2, 1.09 -0.22)')})


    def add_tiger(self, **kw):
        self.add_data('tiger',
                     {'place_id': kw.get('place_id', 30000),
                      'parent_place_id': kw.get('parent_place_id'),
                      'startnumber': kw.get('startnumber', 2),
                      'endnumber': kw.get('endnumber', 6),
                      'step': kw.get('step', 2),
                      'postcode': kw.get('postcode'),
                      'linegeo': kw.get('geometry', 'LINESTRING(1.1 -0.2, 1.09 -0.22)')})


    def add_postcode(self, **kw):
        self.add_data('postcode',
                     {'place_id': kw.get('place_id', 1000),
                      'parent_place_id': kw.get('parent_place_id'),
                      'country_code': kw.get('country_code'),
                      'postcode': kw.get('postcode'),
                      'rank_search': kw.get('rank_search', 20),
                      'rank_address': kw.get('rank_address', 22),
                      'indexed_date': kw.get('indexed_date',
                                             dt.datetime(2022, 12, 7, 14, 14, 46, 0)),
                      'geometry': kw.get('geometry', 'POINT(23 34)')})


    def add_country(self, country_code, geometry):
        self.add_data('country_grid',
                      {'country_code': country_code,
                       'area': 0.1,
                       'geometry': geometry})


    def add_country_name(self, country_code, names, partition=0):
        self.add_data('country_name',
                      {'country_code': country_code,
                       'name': names,
                       'partition': partition})


    def add_search_name(self, place_id, **kw):
        centroid = kw.get('centroid', (23.0, 34.0))
        self.add_data('search_name',
                      {'place_id': place_id,
                       'importance': kw.get('importance', 0.00001),
                       'search_rank': kw.get('search_rank', 30),
                       'address_rank': kw.get('address_rank', 30),
                       'name_vector': kw.get('names', []),
                       'nameaddress_vector': kw.get('address', []),
                       'country_code': kw.get('country_code', 'xx'),
                       'centroid': 'POINT(%f %f)' % centroid})


    def add_class_type_table(self, cls, typ):
        self.async_to_sync(
            self.exec_async(sa.text(f"""CREATE TABLE place_classtype_{cls}_{typ}
                                         AS (SELECT place_id, centroid FROM placex
                                             WHERE class = '{cls}' AND type = '{typ}')
                                     """)))


    def add_word_table(self, content):
        data = [dict(zip(['word_id', 'word_token', 'type', 'word', 'info'], c))
                for c in content]

        async def _do_sql():
            async with self.api._async_api.begin() as conn:
                if 'word' not in conn.t.meta.tables:
                    await make_query_analyzer(conn)
                    word_table = conn.t.meta.tables['word']
                    await conn.connection.run_sync(word_table.create)
                if data:
                    await conn.execute(conn.t.meta.tables['word'].insert(), data)

        self.async_to_sync(_do_sql())


    async def exec_async(self, sql, *args, **kwargs):
        async with self.api._async_api.begin() as conn:
            return await conn.execute(sql, *args, **kwargs)


    async def create_tables(self):
        async with self.api._async_api._engine.begin() as conn:
            await conn.run_sync(self.api._async_api._tables.meta.create_all)


@pytest.fixture
def apiobj(temp_db_with_extensions, temp_db_conn, monkeypatch):
    """ Create an asynchronous SQLAlchemy engine for the test DB.
    """
    monkeypatch.setenv('NOMINATIM_USE_US_TIGER_DATA', 'yes')
    testapi = APITester()
    testapi.async_to_sync(testapi.create_tables())

    proc = SQLPreprocessor(temp_db_conn, testapi.api.config)
    proc.run_sql_file(temp_db_conn, 'functions/ranking.sql')

    loglib.set_log_output('text')
    yield testapi
    print(loglib.get_and_disable())

    testapi.api.close()


@pytest.fixture(params=['postgres_db', 'sqlite_db'])
def frontend(request, event_loop, tmp_path):
    testapis = []
    if request.param == 'sqlite_db':
        db = str(tmp_path / 'test_nominatim_python_unittest.sqlite')

        def mkapi(apiobj, options={'reverse'}):
            apiobj.add_data('properties',
                        [{'property': 'tokenizer', 'value': 'icu'},
                         {'property': 'tokenizer_import_normalisation', 'value': ':: lower();'},
                         {'property': 'tokenizer_import_transliteration', 'value': "'1' > '/1/'; 'ä' > 'ä '"},
                        ])

            async def _do_sql():
                async with apiobj.api._async_api.begin() as conn:
                    if 'word' in conn.t.meta.tables:
                        return
                    await make_query_analyzer(conn)
                    word_table = conn.t.meta.tables['word']
                    await conn.connection.run_sync(word_table.create)

            apiobj.async_to_sync(_do_sql())

            event_loop.run_until_complete(convert_sqlite.convert(Path('/invalid'),
                                                                 db, options))
            outapi = napi.NominatimAPI(Path('/invalid'),
                                       {'NOMINATIM_DATABASE_DSN': f"sqlite:dbname={db}",
                                        'NOMINATIM_USE_US_TIGER_DATA': 'yes'})
            testapis.append(outapi)

            return outapi
    elif request.param == 'postgres_db':
        def mkapi(apiobj, options=None):
            return apiobj.api

    yield mkapi

    for api in testapis:
        api.close()
