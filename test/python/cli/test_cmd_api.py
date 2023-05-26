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


@pytest.mark.parametrize('endpoint, params', [('search', ('--query', 'Berlin')),
                                              ('search_address', ('--city', 'Berlin'))
                                             ])
def test_search(cli_call, tmp_path, capsys, monkeypatch, endpoint, params):
    result = napi.SearchResult(napi.SourceTable.PLACEX, ('place', 'thing'),
                                napi.Point(1.0, -3.0),
                                names={'name':'Name', 'name:fr': 'Nom'},
                                extratags={'extra':'Extra'})

    monkeypatch.setattr(napi.NominatimAPI, endpoint,
                        lambda *args, **kwargs: napi.SearchResults([result]))


    result = cli_call('search', '--project-dir', str(tmp_path), *params)

    assert result == 0

    out = json.loads(capsys.readouterr().out)
    assert len(out) == 1
    assert out[0]['name'] == 'Name'
    assert 'address' not in out[0]
    assert 'extratags' not in out[0]
    assert 'namedetails' not in out[0]
