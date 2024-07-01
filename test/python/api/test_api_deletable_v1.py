# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the deletable v1 API call.
"""
import json
from pathlib import Path

import pytest
import pytest_asyncio

import psycopg2.extras

from fake_adaptor import FakeAdaptor, FakeError, FakeResponse

import nominatim_api.v1.server_glue as glue
import nominatim_api as napi

@pytest_asyncio.fixture
async def api():
    api = napi.NominatimAPIAsync(Path('/invalid'))
    yield api
    await api.close()


class TestDeletableEndPoint:

    @pytest.fixture(autouse=True)
    def setup_deletable_table(self, temp_db_cursor, table_factory, temp_db_with_extensions):
        psycopg2.extras.register_hstore(temp_db_cursor)
        table_factory('import_polygon_delete',
                      definition='osm_id bigint, osm_type char(1), class text, type text',
                      content=[(345, 'N', 'boundary', 'administrative'),
                               (781, 'R', 'landuse', 'wood'),
                               (781, 'R', 'landcover', 'grass')])
        table_factory('placex',
                      definition="""place_id bigint, osm_id bigint, osm_type char(1),
                                    class text, type text, name HSTORE, country_code char(2)""",
                      content=[(1, 345, 'N', 'boundary', 'administrative', {'old_name': 'Former'}, 'ab'),
                               (2, 781, 'R', 'landuse', 'wood', {'name': 'Wood'}, 'cd'),
                               (3, 781, 'R', 'landcover', 'grass', None, 'cd')])



    @pytest.mark.asyncio
    async def test_deletable(self, api):
        a = FakeAdaptor()

        resp = await glue.deletable_endpoint(api, a)
        results = json.loads(resp.output)

        results.sort(key=lambda r: r['place_id'])

        assert results == [{'place_id': 1, 'country_code': 'ab', 'name': None,
                            'osm_id': 345, 'osm_type': 'N',
                            'class': 'boundary', 'type': 'administrative'},
                           {'place_id': 2, 'country_code': 'cd', 'name': 'Wood',
                            'osm_id': 781, 'osm_type': 'R',
                            'class': 'landuse', 'type': 'wood'},
                           {'place_id': 3, 'country_code': 'cd', 'name': None,
                            'osm_id': 781, 'osm_type': 'R',
                            'class': 'landcover', 'type': 'grass'}]

