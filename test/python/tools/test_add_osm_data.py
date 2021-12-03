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


def test_import_osm_file_simple(table_factory, osm2pgsql_options, capfd):
    table_factory('place', content=((1, ), ))

    assert add_osm_data.add_data_from_file(Path('change.osm'), osm2pgsql_options) == 0
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
def test_import_osm_object_main_api(osm2pgsql_options, monkeypatch, capfd,
                                    osm_type, main_api, url):
    get_url_mock = CaptureGetUrl(monkeypatch)

    add_osm_data.add_osm_object(osm_type, 4536, main_api, osm2pgsql_options)
    captured = capfd.readouterr()

    assert get_url_mock.url.startswith(url)

    assert '--append' in captured.out
    assert '--output gazetteer' in captured.out
    assert f'--style {osm2pgsql_options["osm2pgsql_style"]}' in captured.out
    assert f'--number-processes {osm2pgsql_options["threads"]}' in captured.out
    assert f'--cache {osm2pgsql_options["osm2pgsql_cache"]}' in captured.out
    assert captured.out.endswith(' -\n')
