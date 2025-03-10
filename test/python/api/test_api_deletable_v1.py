# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the deletable v1 API call.
"""
import json

import pytest

from fake_adaptor import FakeAdaptor

import nominatim_api.v1.server_glue as glue


class TestDeletableEndPoint:

    @pytest.fixture(autouse=True)
    def setup_deletable_table(self, temp_db_cursor, table_factory, temp_db_with_extensions):
        table_factory('import_polygon_delete',
                      definition='osm_id bigint, osm_type char(1), class text, type text',
                      content=[(345, 'N', 'boundary', 'administrative'),
                               (781, 'R', 'landuse', 'wood'),
                               (781, 'R', 'landcover', 'grass')])
        table_factory(
            'placex',
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
