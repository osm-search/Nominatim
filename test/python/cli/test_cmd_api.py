# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for API access commands of command-line interface wrapper.
"""
import json
import pytest

import nominatim.clicmd.api
import nominatim.api
from nominatim.apicmd.status import StatusResult


@pytest.mark.parametrize("endpoint", (('search', 'reverse', 'lookup', 'details', 'status')))
def test_no_api_without_phpcgi(endpoint):
    assert nominatim.cli.nominatim(module_dir='MODULE NOT AVAILABLE',
                                   osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                   phpcgi_path=None,
                                   cli_args=[endpoint]) == 1


@pytest.mark.parametrize("params", [('search', '--query', 'new'),
                                    ('search', '--city', 'Berlin'),
                                    ('reverse', '--lat', '0', '--lon', '0', '--zoom', '13'),
                                    ('lookup', '--id', 'N1'),
                                    ('details', '--node', '1'),
                                    ('details', '--way', '1'),
                                    ('details', '--relation', '1'),
                                    ('details', '--place_id', '10001')])
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
        monkeypatch.setattr(nominatim.api.NominatimAPI, 'status',
                            lambda self: StatusResult(200, 'OK'))


    def test_status_simple(self, cli_call, tmp_path):
        result = cli_call('status', '--project-dir', str(tmp_path))

        assert result == 0


    def test_status_json_format(self, cli_call, tmp_path, capsys):
        result = cli_call('status', '--project-dir', str(tmp_path),
                          '--format', 'json')

        assert result == 0

        json.loads(capsys.readouterr().out)


QUERY_PARAMS = {
 'search': ('--query', 'somewhere'),
 'reverse': ('--lat', '20', '--lon', '30'),
 'lookup': ('--id', 'R345345'),
 'details': ('--node', '324')
}

@pytest.mark.parametrize("endpoint", (('search', 'reverse', 'lookup')))
class TestCliApiCommonParameters:

    @pytest.fixture(autouse=True)
    def setup_website_dir(self, cli_call, project_env, endpoint):
        self.endpoint = endpoint
        self.cli_call = cli_call
        self.project_dir = project_env.project_dir
        (self.project_dir / 'website').mkdir()


    def expect_param(self, param, expected):
        (self.project_dir / 'website' / (self.endpoint + '.php')).write_text(f"""<?php
        exit($_GET['{param}']  == '{expected}' ? 0 : 10);
        """)


    def call_nominatim(self, *params):
        return self.cli_call(self.endpoint, *QUERY_PARAMS[self.endpoint],
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

    assert cli_call('search', *QUERY_PARAMS['search'], '--project-dir', str(project_env.project_dir),
                    '--bounded') == 0


def test_cli_search_param_dedupe(cli_call, project_env):
    webdir = project_env.project_dir / 'website'
    webdir.mkdir()
    (webdir / 'search.php').write_text(f"""<?php
        exit($_GET['dedupe']  == '0' ? 0 : 10);
        """)

    assert cli_call('search', *QUERY_PARAMS['search'], '--project-dir', str(project_env.project_dir),
                    '--no-dedupe') == 0


def test_cli_details_param_class(cli_call, project_env):
    webdir = project_env.project_dir / 'website'
    webdir.mkdir()
    (webdir / 'details.php').write_text(f"""<?php
        exit($_GET['class']  == 'highway' ? 0 : 10);
        """)

    assert cli_call('details', *QUERY_PARAMS['details'], '--project-dir', str(project_env.project_dir),
                    '--class', 'highway') == 0


@pytest.mark.parametrize('param', ('lang', 'accept-language'))
def test_cli_details_param_lang(cli_call, project_env, param):
    webdir = project_env.project_dir / 'website'
    webdir.mkdir()
    (webdir / 'details.php').write_text(f"""<?php
        exit($_GET['accept-language']  == 'es' ? 0 : 10);
        """)

    assert cli_call('details', *QUERY_PARAMS['details'], '--project-dir', str(project_env.project_dir),
                    '--' + param, 'es') == 0

