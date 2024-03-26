# SPDX-FileCopyrightText: 2023 Nominatim developer community <https://nominatim.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the deletable v1 API call.
"""
import json
import datetime as dt
from pathlib import Path

import pytest
import pytest_asyncio

import psycopg2.extras

from fake_adaptor import FakeAdaptor, FakeError, FakeResponse

import nominatim.api.v1.server_glue as glue
import nominatim.api as napi

@pytest_asyncio.fixture
async def api():
    api = napi.NominatimAPIAsync(Path('/invalid'))
    yield api
    await api.close()


class TestPolygonsEndPoint:

    @pytest.fixture(autouse=True)
    def setup_deletable_table(self, temp_db_cursor, table_factory, temp_db_with_extensions):
        psycopg2.extras.register_hstore(temp_db_cursor)

        self.now = dt.datetime.now()
        self.recent = dt.datetime.now() - dt.timedelta(days=3)

        table_factory('import_polygon_error',
                      definition="""osm_id bigint,
                                    osm_type character(1),
                                    class text,
                                    type text,
                                    name hstore,
                                    country_code character varying(2),
                                    updated timestamp without time zone,
                                    errormessage text,
                                    prevgeometry geometry(Geometry,4326),
                                    newgeometry geometry(Geometry,4326)""",
                    content=[(345, 'N', 'boundary', 'administrative',
                              {'name': 'Foo'}, 'xx', self.recent,
                              'some text', None, None),
                             (781, 'R', 'landuse', 'wood',
                              None, 'ds', self.now,
                              'Area reduced by lots', None, None)])


    @pytest.mark.asyncio
    async def test_polygons_simple(self, api):
        a = FakeAdaptor()

        resp = await glue.polygons_endpoint(api, a)
        results = json.loads(resp.output)

        results.sort(key=lambda r: (r['osm_type'], r['osm_id']))

        assert results == [{'osm_type': 'N', 'osm_id': 345,
                            'class': 'boundary', 'type': 'administrative',
                            'name': 'Foo', 'country_code': 'xx',
                            'errormessage': 'some text',
                            'updated': self.recent.isoformat(sep=' ', timespec='seconds')},
                           {'osm_type': 'R', 'osm_id': 781,
                            'class': 'landuse', 'type': 'wood',
                            'name': None, 'country_code': 'ds',
                            'errormessage': 'Area reduced by lots',
                            'updated': self.now.isoformat(sep=' ', timespec='seconds')}]


    @pytest.mark.asyncio
    async def test_polygons_days(self, api):
        a = FakeAdaptor()
        a.params['days'] = '2'

        resp = await glue.polygons_endpoint(api, a)
        results = json.loads(resp.output)

        assert [r['osm_id'] for r in results] == [781]


    @pytest.mark.asyncio
    async def test_polygons_class(self, api):
        a = FakeAdaptor()
        a.params['class'] = 'landuse'

        resp = await glue.polygons_endpoint(api, a)
        results = json.loads(resp.output)

        assert [r['osm_id'] for r in results] == [781]



    @pytest.mark.asyncio
    async def test_polygons_reduced(self, api):
        a = FakeAdaptor()
        a.params['reduced'] = '1'

        resp = await glue.polygons_endpoint(api, a)
        results = json.loads(resp.output)

        assert [r['osm_id'] for r in results] == [781]
