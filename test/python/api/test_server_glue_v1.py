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
Tests for the Python web frameworks adaptor, v1 API.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from fake_adaptor import FakeAdaptor, FakeError, FakeResponse

import nominatim.api.v1.server_glue as glue
import nominatim.api as napi
import nominatim.api.logging as loglib


# ASGIAdaptor.get_int/bool()

@pytest.mark.parametrize('func', ['get_int', 'get_bool'])
def test_adaptor_get_int_missing_but_required(func):
    with pytest.raises(FakeError, match='^400 -- .*missing'):
        getattr(FakeAdaptor(), func)('something')


@pytest.mark.parametrize('func, val', [('get_int', 23), ('get_bool', True)])
def test_adaptor_get_int_missing_with_default(func, val):
    assert getattr(FakeAdaptor(), func)('something', val) == val


@pytest.mark.parametrize('inp', ['0', '234', '-4566953498567934876'])
def test_adaptor_get_int_success(inp):
    assert FakeAdaptor(params={'foo': inp}).get_int('foo') == int(inp)
    assert FakeAdaptor(params={'foo': inp}).get_int('foo', 4) == int(inp)


@pytest.mark.parametrize('inp', ['rs', '4.5', '6f'])
def test_adaptor_get_int_bad_number(inp):
    with pytest.raises(FakeError, match='^400 -- .*must be a number'):
        FakeAdaptor(params={'foo': inp}).get_int('foo')


@pytest.mark.parametrize('inp', ['1', 'true', 'whatever', 'false'])
def test_adaptor_get_bool_trueish(inp):
    assert FakeAdaptor(params={'foo': inp}).get_bool('foo')


def test_adaptor_get_bool_falsish():
    assert not FakeAdaptor(params={'foo': '0'}).get_bool('foo')


# ASGIAdaptor.parse_format()

def test_adaptor_parse_format_use_default():
    adaptor = FakeAdaptor()

    assert adaptor.parse_format(napi.StatusResult, 'text') == 'text'
    assert adaptor.content_type == 'text/plain; charset=utf-8'


def test_adaptor_parse_format_use_configured():
    adaptor = FakeAdaptor(params={'format': 'json'})

    assert adaptor.parse_format(napi.StatusResult, 'text') == 'json'
    assert adaptor.content_type == 'application/json'


def test_adaptor_parse_format_invalid_value():
    adaptor = FakeAdaptor(params={'format': '@!#'})

    with pytest.raises(FakeError, match='^400 -- .*must be one of'):
        adaptor.parse_format(napi.StatusResult, 'text')


# ASGIAdaptor.get_accepted_languages()

def test_accepted_languages_from_param():
    a = FakeAdaptor(params={'accept-language': 'de'})
    assert a.get_accepted_languages() == 'de'


def test_accepted_languages_from_header():
    a = FakeAdaptor(headers={'accept-language': 'de'})
    assert a.get_accepted_languages() == 'de'


def test_accepted_languages_from_default(monkeypatch):
    monkeypatch.setenv('NOMINATIM_DEFAULT_LANGUAGE', 'de')
    a = FakeAdaptor()
    assert a.get_accepted_languages() == 'de'


def test_accepted_languages_param_over_header():
    a = FakeAdaptor(params={'accept-language': 'de'},
                    headers={'accept-language': 'en'})
    assert a.get_accepted_languages() == 'de'


def test_accepted_languages_header_over_default(monkeypatch):
    monkeypatch.setenv('NOMINATIM_DEFAULT_LANGUAGE', 'en')
    a = FakeAdaptor(headers={'accept-language': 'de'})
    assert a.get_accepted_languages() == 'de'


# ASGIAdaptor.raise_error()

class TestAdaptorRaiseError:

    @pytest.fixture(autouse=True)
    def init_adaptor(self):
        self.adaptor = FakeAdaptor()
        self.adaptor.setup_debugging()

    def run_raise_error(self, msg, status):
        with pytest.raises(FakeError) as excinfo:
            self.adaptor.raise_error(msg, status=status)

        return excinfo.value


    def test_without_content_set(self):
        err = self.run_raise_error('TEST', 404)

        assert self.adaptor.content_type == 'text/plain; charset=utf-8'
        assert err.msg == 'TEST'
        assert err.status == 404


    def test_json(self):
        self.adaptor.content_type = 'application/json'

        err = self.run_raise_error('TEST', 501)

        content = json.loads(err.msg)['error']
        assert content['code'] == 501
        assert content['message'] == 'TEST'


    def test_xml(self):
        self.adaptor.content_type = 'text/xml; charset=utf-8'

        err = self.run_raise_error('this!', 503)

        content = ET.fromstring(err.msg)

        assert content.tag == 'error'
        assert content.find('code').text == '503'
        assert content.find('message').text == 'this!'


def test_raise_error_during_debug():
    a = FakeAdaptor(params={'debug': '1'})
    a.setup_debugging()
    loglib.log().section('Ongoing')

    with pytest.raises(FakeError) as excinfo:
        a.raise_error('badstate')

    content = ET.fromstring(excinfo.value.msg)

    assert content.tag == 'html'

    assert '>Ongoing<' in excinfo.value.msg
    assert 'badstate' in excinfo.value.msg


# ASGIAdaptor.build_response

def test_build_response_without_content_type():
    resp = FakeAdaptor().build_response('attention')

    assert isinstance(resp, FakeResponse)
    assert resp.status == 200
    assert resp.output == 'attention'
    assert resp.content_type == 'text/plain; charset=utf-8'


def test_build_response_with_status():
    a = FakeAdaptor(params={'format': 'json'})
    a.parse_format(napi.StatusResult, 'text')

    resp = a.build_response('stuff\nmore stuff', status=404)

    assert isinstance(resp, FakeResponse)
    assert resp.status == 404
    assert resp.output == 'stuff\nmore stuff'
    assert resp.content_type == 'application/json'


def test_build_response_jsonp_with_json():
    a = FakeAdaptor(params={'format': 'json', 'json_callback': 'test.func'})
    a.parse_format(napi.StatusResult, 'text')

    resp = a.build_response('{}')

    assert isinstance(resp, FakeResponse)
    assert resp.status == 200
    assert resp.output == 'test.func({})'
    assert resp.content_type == 'application/javascript'


def test_build_response_jsonp_without_json():
    a = FakeAdaptor(params={'format': 'text', 'json_callback': 'test.func'})
    a.parse_format(napi.StatusResult, 'text')

    resp = a.build_response('{}')

    assert isinstance(resp, FakeResponse)
    assert resp.status == 200
    assert resp.output == '{}'
    assert resp.content_type == 'text/plain; charset=utf-8'


@pytest.mark.parametrize('param', ['alert(); func', '\\n', '', 'a b'])
def test_build_response_jsonp_bad_format(param):
    a = FakeAdaptor(params={'format': 'json', 'json_callback': param})
    a.parse_format(napi.StatusResult, 'text')

    with pytest.raises(FakeError, match='^400 -- .*Invalid'):
        a.build_response('{}')


# status_endpoint()

class TestStatusEndpoint:

    @pytest.fixture(autouse=True)
    def patch_status_func(self, monkeypatch):
        async def _status(*args, **kwargs):
            return self.status

        monkeypatch.setattr(napi.NominatimAPIAsync, 'status', _status)


    @pytest.mark.asyncio
    async def test_status_without_params(self):
        a = FakeAdaptor()
        self.status = napi.StatusResult(0, 'foo')

        resp = await glue.status_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert isinstance(resp, FakeResponse)
        assert resp.status == 200
        assert resp.content_type == 'text/plain; charset=utf-8'


    @pytest.mark.asyncio
    async def test_status_with_error(self):
        a = FakeAdaptor()
        self.status = napi.StatusResult(405, 'foo')

        resp = await glue.status_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert isinstance(resp, FakeResponse)
        assert resp.status == 500
        assert resp.content_type == 'text/plain; charset=utf-8'


    @pytest.mark.asyncio
    async def test_status_json_with_error(self):
        a = FakeAdaptor(params={'format': 'json'})
        self.status = napi.StatusResult(405, 'foo')

        resp = await glue.status_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert isinstance(resp, FakeResponse)
        assert resp.status == 200
        assert resp.content_type == 'application/json'


    @pytest.mark.asyncio
    async def test_status_bad_format(self):
        a = FakeAdaptor(params={'format': 'foo'})
        self.status = napi.StatusResult(0, 'foo')

        with pytest.raises(FakeError):
            await glue.status_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)


# details_endpoint()

class TestDetailsEndpoint:

    @pytest.fixture(autouse=True)
    def patch_lookup_func(self, monkeypatch):
        self.result = napi.DetailedResult(napi.SourceTable.PLACEX,
                                          ('place', 'thing'),
                                          napi.Point(1.0, 2.0))
        self.lookup_args = []

        async def _lookup(*args, **kwargs):
            self.lookup_args.extend(args[1:])
            return self.result

        monkeypatch.setattr(napi.NominatimAPIAsync, 'details', _lookup)


    @pytest.mark.asyncio
    async def test_details_no_params(self):
        a = FakeAdaptor()

        with pytest.raises(FakeError, match='^400 -- .*Missing'):
            await glue.details_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)


    @pytest.mark.asyncio
    async def test_details_by_place_id(self):
        a = FakeAdaptor(params={'place_id': '4573'})

        await glue.details_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert self.lookup_args[0].place_id == 4573


    @pytest.mark.asyncio
    async def test_details_by_osm_id(self):
        a = FakeAdaptor(params={'osmtype': 'N', 'osmid': '45'})

        await glue.details_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert self.lookup_args[0].osm_type == 'N'
        assert self.lookup_args[0].osm_id == 45
        assert self.lookup_args[0].osm_class is None


    @pytest.mark.asyncio
    async def test_details_with_debugging(self):
        a = FakeAdaptor(params={'osmtype': 'N', 'osmid': '45', 'debug': '1'})

        resp = await glue.details_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)
        content = ET.fromstring(resp.output)

        assert resp.content_type == 'text/html; charset=utf-8'
        assert content.tag == 'html'


    @pytest.mark.asyncio
    async def test_details_no_result(self):
        a = FakeAdaptor(params={'place_id': '4573'})
        self.result = None

        with pytest.raises(FakeError, match='^404 -- .*found'):
            await glue.details_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)


# reverse_endpoint()
class TestReverseEndPoint:

    @pytest.fixture(autouse=True)
    def patch_reverse_func(self, monkeypatch):
        self.result = napi.ReverseResult(napi.SourceTable.PLACEX,
                                          ('place', 'thing'),
                                          napi.Point(1.0, 2.0))
        async def _reverse(*args, **kwargs):
            return self.result

        monkeypatch.setattr(napi.NominatimAPIAsync, 'reverse', _reverse)


    @pytest.mark.asyncio
    @pytest.mark.parametrize('params', [{}, {'lat': '3.4'}, {'lon': '6.7'}])
    async def test_reverse_no_params(self, params):
        a = FakeAdaptor()
        a.params = params
        a.params['format'] = 'xml'

        with pytest.raises(FakeError, match='^400 -- (?s:.*)missing'):
            await glue.reverse_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)


    @pytest.mark.asyncio
    @pytest.mark.parametrize('params', [{'lat': '45.6', 'lon': '4563'}])
    async def test_reverse_success(self, params):
        a = FakeAdaptor()
        a.params = params
        a.params['format'] = 'json'

        res = await glue.reverse_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert res == ''


    @pytest.mark.asyncio
    async def test_reverse_success(self):
        a = FakeAdaptor()
        a.params['lat'] = '56.3'
        a.params['lon'] = '6.8'

        assert await glue.reverse_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)


    @pytest.mark.asyncio
    async def test_reverse_from_search(self):
        a = FakeAdaptor()
        a.params['q'] = '34.6 2.56'
        a.params['format'] = 'json'

        res = await glue.search_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1


# lookup_endpoint()

class TestLookupEndpoint:

    @pytest.fixture(autouse=True)
    def patch_lookup_func(self, monkeypatch):
        self.results = [napi.SearchResult(napi.SourceTable.PLACEX,
                                          ('place', 'thing'),
                                          napi.Point(1.0, 2.0))]
        async def _lookup(*args, **kwargs):
            return napi.SearchResults(self.results)

        monkeypatch.setattr(napi.NominatimAPIAsync, 'lookup', _lookup)


    @pytest.mark.asyncio
    async def test_lookup_no_params(self):
        a = FakeAdaptor()
        a.params['format'] = 'json'

        res = await glue.lookup_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert res.output == '[]'


    @pytest.mark.asyncio
    @pytest.mark.parametrize('param', ['w', 'bad', ''])
    async def test_lookup_bad_params(self, param):
        a = FakeAdaptor()
        a.params['format'] = 'json'
        a.params['osm_ids'] = f'W34,{param},N33333'

        res = await glue.lookup_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1


    @pytest.mark.asyncio
    @pytest.mark.parametrize('param', ['p234234', '4563'])
    async def test_lookup_bad_osm_type(self, param):
        a = FakeAdaptor()
        a.params['format'] = 'json'
        a.params['osm_ids'] = f'W34,{param},N33333'

        res = await glue.lookup_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1


    @pytest.mark.asyncio
    async def test_lookup_working(self):
        a = FakeAdaptor()
        a.params['format'] = 'json'
        a.params['osm_ids'] = 'N23,W34'

        res = await glue.lookup_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1


# search_endpoint()

class TestSearchEndPointSearch:

    @pytest.fixture(autouse=True)
    def patch_lookup_func(self, monkeypatch):
        self.results = [napi.SearchResult(napi.SourceTable.PLACEX,
                                          ('place', 'thing'),
                                          napi.Point(1.0, 2.0))]
        async def _search(*args, **kwargs):
            return napi.SearchResults(self.results)

        monkeypatch.setattr(napi.NominatimAPIAsync, 'search', _search)


    @pytest.mark.asyncio
    async def test_search_free_text(self):
        a = FakeAdaptor()
        a.params['q'] = 'something'

        res = await glue.search_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1


    @pytest.mark.asyncio
    async def test_search_free_text_xml(self):
        a = FakeAdaptor()
        a.params['q'] = 'something'
        a.params['format'] = 'xml'

        res = await glue.search_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert res.status == 200
        assert res.output.index('something') > 0


    @pytest.mark.asyncio
    async def test_search_free_and_structured(self):
        a = FakeAdaptor()
        a.params['q'] = 'something'
        a.params['city'] = 'ignored'

        res = await glue.search_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1


    @pytest.mark.asyncio
    @pytest.mark.parametrize('dedupe,numres', [(True, 1), (False, 2)])
    async def test_search_dedupe(self, dedupe, numres):
        self.results = self.results * 2
        a = FakeAdaptor()
        a.params['q'] = 'something'
        if not dedupe:
            a.params['dedupe'] = '0'

        res = await glue.search_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == numres


class TestSearchEndPointSearchAddress:

    @pytest.fixture(autouse=True)
    def patch_lookup_func(self, monkeypatch):
        self.results = [napi.SearchResult(napi.SourceTable.PLACEX,
                                          ('place', 'thing'),
                                          napi.Point(1.0, 2.0))]
        async def _search(*args, **kwargs):
            return napi.SearchResults(self.results)

        monkeypatch.setattr(napi.NominatimAPIAsync, 'search_address', _search)


    @pytest.mark.asyncio
    async def test_search_structured(self):
        a = FakeAdaptor()
        a.params['street'] = 'something'

        res = await glue.search_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1


class TestSearchEndPointSearchCategory:

    @pytest.fixture(autouse=True)
    def patch_lookup_func(self, monkeypatch):
        self.results = [napi.SearchResult(napi.SourceTable.PLACEX,
                                          ('place', 'thing'),
                                          napi.Point(1.0, 2.0))]
        async def _search(*args, **kwargs):
            return napi.SearchResults(self.results)

        monkeypatch.setattr(napi.NominatimAPIAsync, 'search_category', _search)


    @pytest.mark.asyncio
    async def test_search_category(self):
        a = FakeAdaptor()
        a.params['q'] = '[shop=fog]'

        res = await glue.search_endpoint(napi.NominatimAPIAsync(Path('/invalid')), a)

        assert len(json.loads(res.output)) == 1
