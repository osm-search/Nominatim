# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for API access commands of command-line interface wrapper.
"""
import json
import pytest

import nominatim.clicmd.api
import nominatim.api as napi


@pytest.mark.parametrize("endpoint", (('search', 'reverse', 'lookup', 'details', 'status')))
def test_no_api_without_phpcgi(endpoint):
    assert nominatim.cli.nominatim(module_dir='MODULE NOT AVAILABLE',
                                   osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                   phpcgi_path=None,
                                   cli_args=[endpoint]) == 1


@pytest.mark.parametrize("params", [('search', '--query', 'new'),
                                    ('search', '--city', 'Berlin')])
class TestCliApiCallPhp:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, params, cli_call, mock_func_factory, tmp_path):
        self.mock_run_api = mock_func_factory(nominatim.clicmd.api, 'run_api_script')

        def _run():
            return cli_call(*params, '--project-dir', str(tmp_path))

        self.run_nominatim = _run


    def test_api_commands_simple(self, tmp_path, params):
        (tmp_path / 'website').mkdir()
        (tmp_path / 'website' / (params[0] + '.php')).write_text('')

        assert self.run_nominatim() == 0

        assert self.mock_run_api.called == 1
        assert self.mock_run_api.last_args[0] == params[0]


    def test_bad_project_dir(self):
        assert self.run_nominatim() == 1


class TestCliStatusCall:

    @pytest.fixture(autouse=True)
    def setup_status_mock(self, monkeypatch):
        monkeypatch.setattr(napi.NominatimAPI, 'status',
                            lambda self: napi.StatusResult(200, 'OK'))


    def test_status_simple(self, cli_call, tmp_path):
        result = cli_call('status', '--project-dir', str(tmp_path))

        assert result == 0


    def test_status_json_format(self, cli_call, tmp_path, capsys):
        result = cli_call('status', '--project-dir', str(tmp_path),
                          '--format', 'json')

        assert result == 0

        json.loads(capsys.readouterr().out)


class TestCliDetailsCall:

    @pytest.fixture(autouse=True)
    def setup_status_mock(self, monkeypatch):
        result = napi.DetailedResult(napi.SourceTable.PLACEX, ('place', 'thing'),
                                     napi.Point(1.0, -3.0))

        monkeypatch.setattr(napi.NominatimAPI, 'details',
                            lambda *args, **kwargs: result)

    @pytest.mark.parametrize("params", [('--node', '1'),
                                        ('--way', '1'),
                                        ('--relation', '1'),
                                        ('--place_id', '10001')])

    def test_details_json_format(self, cli_call, tmp_path, capsys, params):
        result = cli_call('details', '--project-dir', str(tmp_path), *params)

        assert result == 0

        json.loads(capsys.readouterr().out)


class TestCliReverseCall:

    @pytest.fixture(autouse=True)
    def setup_reverse_mock(self, monkeypatch):
        result = napi.ReverseResult(napi.SourceTable.PLACEX, ('place', 'thing'),
                                    napi.Point(1.0, -3.0),
                                    names={'name':'Name', 'name:fr': 'Nom'},
                                    extratags={'extra':'Extra'})

        monkeypatch.setattr(napi.NominatimAPI, 'reverse',
                            lambda *args, **kwargs: result)


    def test_reverse_simple(self, cli_call, tmp_path, capsys):
        result = cli_call('reverse', '--project-dir', str(tmp_path),
                          '--lat', '34', '--lon', '34')

        assert result == 0

        out = json.loads(capsys.readouterr().out)
        assert out['name'] == 'Name'
        assert 'address' not in out
        assert 'extratags' not in out
        assert 'namedetails' not in out


    @pytest.mark.parametrize('param,field', [('--addressdetails', 'address'),
                                             ('--extratags', 'extratags'),
                                             ('--namedetails', 'namedetails')])
    def test_reverse_extra_stuff(self, cli_call, tmp_path, capsys, param, field):
        result = cli_call('reverse', '--project-dir', str(tmp_path),
                          '--lat', '34', '--lon', '34', param)

        assert result == 0

        out = json.loads(capsys.readouterr().out)
        assert field in out


    def test_reverse_format(self, cli_call, tmp_path, capsys):
        result = cli_call('reverse', '--project-dir', str(tmp_path),
                          '--lat', '34', '--lon', '34', '--format', 'geojson')

        assert result == 0

        out = json.loads(capsys.readouterr().out)
        assert out['type'] == 'FeatureCollection'


    def test_reverse_language(self, cli_call, tmp_path, capsys):
        result = cli_call('reverse', '--project-dir', str(tmp_path),
                          '--lat', '34', '--lon', '34', '--lang', 'fr')

        assert result == 0

        out = json.loads(capsys.readouterr().out)
        assert out['name'] == 'Nom'


class TestCliLookupCall:

    @pytest.fixture(autouse=True)
    def setup_lookup_mock(self, monkeypatch):
        result = napi.SearchResult(napi.SourceTable.PLACEX, ('place', 'thing'),
                                    napi.Point(1.0, -3.0),
                                    names={'name':'Name', 'name:fr': 'Nom'},
                                    extratags={'extra':'Extra'})

        monkeypatch.setattr(napi.NominatimAPI, 'lookup',
                            lambda *args, **kwargs: napi.SearchResults([result]))

    def test_lookup_simple(self, cli_call, tmp_path, capsys):
        result = cli_call('lookup', '--project-dir', str(tmp_path),
                          '--id', 'N34')

        assert result == 0

        out = json.loads(capsys.readouterr().out)
        assert len(out) == 1
        assert out[0]['name'] == 'Name'
        assert 'address' not in out[0]
        assert 'extratags' not in out[0]
        assert 'namedetails' not in out[0]


class TestCliApiCommonParameters:

    @pytest.fixture(autouse=True)
    def setup_website_dir(self, cli_call, project_env):
        self.cli_call = cli_call
        self.project_dir = project_env.project_dir
        (self.project_dir / 'website').mkdir()


    def expect_param(self, param, expected):
        (self.project_dir / 'website' / ('search.php')).write_text(f"""<?php
        exit($_GET['{param}']  == '{expected}' ? 0 : 10);
        """)


    def call_nominatim(self, *params):
        return self.cli_call('search', '--query', 'somewhere',
                             '--project-dir', str(self.project_dir), *params)


    def test_param_output(self):
        self.expect_param('format', 'xml')
        assert self.call_nominatim('--format', 'xml') == 0


    def test_param_lang(self):
        self.expect_param('accept-language', 'de')
        assert self.call_nominatim('--lang', 'de') == 0
        assert self.call_nominatim('--accept-language', 'de') == 0


    @pytest.mark.parametrize("param", ('addressdetails', 'extratags', 'namedetails'))
    def test_param_extradata(self, param):
        self.expect_param(param, '1')

        assert self.call_nominatim('--' + param) == 0

    def test_param_polygon_output(self):
        self.expect_param('polygon_geojson', '1')

        assert self.call_nominatim('--polygon-output', 'geojson') == 0


    def test_param_polygon_threshold(self):
        self.expect_param('polygon_threshold', '0.3452')

        assert self.call_nominatim('--polygon-threshold', '0.3452') == 0


def test_cli_search_param_bounded(cli_call, project_env):
    webdir = project_env.project_dir / 'website'
    webdir.mkdir()
    (webdir / 'search.php').write_text(f"""<?php
        exit($_GET['bounded']  == '1' ? 0 : 10);
        """)

    assert cli_call('search', '--query', 'somewhere', '--project-dir', str(project_env.project_dir),
                    '--bounded') == 0


def test_cli_search_param_dedupe(cli_call, project_env):
    webdir = project_env.project_dir / 'website'
    webdir.mkdir()
    (webdir / 'search.php').write_text(f"""<?php
        exit($_GET['dedupe']  == '0' ? 0 : 10);
        """)

    assert cli_call('search', '--query', 'somewhere', '--project-dir', str(project_env.project_dir),
                    '--no-dedupe') == 0
