# SPDX-FileCopyrightText: 2023 Nominatim developer community <https://nominatim.org>
#
# SPDX-License-Identifier: GPL-2.0-only

# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for functions to add additional data to the database.
"""
from pathlib import Path

import pytest

from nominatim.tools import add_osm_data

class CaptureGetUrl:

    def __init__(self, monkeypatch):
        self.url = None
        monkeypatch.setattr(add_osm_data, 'get_url', self)

    def __call__(self, url):
        self.url = url
        return '<xml></xml>'


@pytest.fixture(autouse=True)
def setup_delete_postprocessing(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION flush_deleted_places()
                              RETURNS INTEGER AS $$ SELECT 1 $$ LANGUAGE SQL""")

def test_import_osm_file_simple(dsn, table_factory, osm2pgsql_options, capfd):

    assert add_osm_data.add_data_from_file(dsn, Path('change.osm'), osm2pgsql_options) == 0
    captured = capfd.readouterr()

    assert '--append' in captured.out
    assert '--output gazetteer' in captured.out
    assert f'--style {osm2pgsql_options["osm2pgsql_style"]}' in captured.out
    assert f'--number-processes {osm2pgsql_options["threads"]}' in captured.out
    assert f'--cache {osm2pgsql_options["osm2pgsql_cache"]}' in captured.out
    assert 'change.osm' in captured.out


@pytest.mark.parametrize("osm_type", ['node', 'way', 'relation'])
@pytest.mark.parametrize("main_api,url", [(True, 'https://www.openstreetmap.org/api'),
                                          (False, 'https://overpass-api.de/api/interpreter?')])
def test_import_osm_object_main_api(dsn, osm2pgsql_options, monkeypatch,
                                    capfd, osm_type, main_api, url):
    get_url_mock = CaptureGetUrl(monkeypatch)

    add_osm_data.add_osm_object(dsn, osm_type, 4536, main_api, osm2pgsql_options)
    captured = capfd.readouterr()

    assert get_url_mock.url.startswith(url)

    assert '--append' in captured.out
    assert '--output gazetteer' in captured.out
    assert f'--style {osm2pgsql_options["osm2pgsql_style"]}' in captured.out
    assert f'--number-processes {osm2pgsql_options["threads"]}' in captured.out
    assert f'--cache {osm2pgsql_options["osm2pgsql_cache"]}' in captured.out
    assert captured.out.endswith(' -\n')
