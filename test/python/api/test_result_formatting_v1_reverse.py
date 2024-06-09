# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for formatting reverse results for the V1 API.

These test only ensure that the Python code is correct.
For functional tests see BDD test suite.
"""
import json
import xml.etree.ElementTree as ET

import pytest

import nominatim_api.v1 as api_impl
import nominatim_api as napi

FORMATS = ['json', 'jsonv2', 'geojson', 'geocodejson', 'xml']

@pytest.mark.parametrize('fmt', FORMATS)
def test_format_reverse_minimal(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('amenity', 'post_box'),
                                 napi.Point(0.3, -8.9))

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt, {})

    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.tag == 'reversegeocode'
    else:
        result = json.loads(raw)
        assert isinstance(result, dict)


@pytest.mark.parametrize('fmt', FORMATS)
def test_format_reverse_no_result(fmt):
    raw = api_impl.format_result(napi.ReverseResults(), fmt, {})

    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.find('error').text == 'Unable to geocode'
    else:
        assert json.loads(raw) == {'error': 'Unable to geocode'}


@pytest.mark.parametrize('fmt', FORMATS)
def test_format_reverse_with_osm_id(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('amenity', 'post_box'),
                                 napi.Point(0.3, -8.9),
                                 place_id=5564,
                                 osm_object=('N', 23))

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt, {})

    if fmt == 'xml':
        root = ET.fromstring(raw).find('result')
        assert root.attrib['osm_type'] == 'node'
        assert root.attrib['osm_id'] == '23'
    else:
        result = json.loads(raw)
        if fmt == 'geocodejson':
            props = result['features'][0]['properties']['geocoding']
        elif fmt == 'geojson':
            props = result['features'][0]['properties']
        else:
            props = result
        assert props['osm_type'] == 'node'
        assert props['osm_id'] == 23


@pytest.mark.parametrize('fmt', FORMATS)
def test_format_reverse_with_address(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 country_code='fe',
                                 address_rows=napi.AddressLines([
                                   napi.AddressLine(place_id=None,
                                                    osm_object=None,
                                                    category=('place', 'county'),
                                                    names={'name': 'Hello'},
                                                    extratags=None,
                                                    admin_level=5,
                                                    fromarea=False,
                                                    isaddress=True,
                                                    rank_address=10,
                                                    distance=0.0),
                                   napi.AddressLine(place_id=None,
                                                    osm_object=None,
                                                    category=('place', 'county'),
                                                    names={'name': 'ByeBye'},
                                                    extratags=None,
                                                    admin_level=5,
                                                    fromarea=False,
                                                    isaddress=False,
                                                    rank_address=10,
                                                    distance=0.0)
                                 ]))
    reverse.localize(napi.Locales())

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                 {'addressdetails': True})


    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.find('addressparts').find('county').text == 'Hello'
    else:
        result = json.loads(raw)
        assert isinstance(result, dict)

        if fmt == 'geocodejson':
            props = result['features'][0]['properties']['geocoding']
            assert 'admin' in props
            assert props['county'] == 'Hello'
        else:
            if fmt == 'geojson':
                props = result['features'][0]['properties']
            else:
                props = result
            assert 'address' in props


def test_format_reverse_geocodejson_special_parts():
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('place', 'house'),
                                 napi.Point(1.0, 2.0),
                                 place_id=33,
                                 country_code='fe',
                                 address_rows=napi.AddressLines([
                                   napi.AddressLine(place_id=None,
                                                    osm_object=None,
                                                    category=('place', 'house_number'),
                                                    names={'ref': '1'},
                                                    extratags=None,
                                                    admin_level=15,
                                                    fromarea=False,
                                                    isaddress=True,
                                                    rank_address=10,
                                                    distance=0.0),
                                   napi.AddressLine(place_id=None,
                                                    osm_object=None,
                                                    category=('place', 'postcode'),
                                                    names={'ref': '99446'},
                                                    extratags=None,
                                                    admin_level=11,
                                                    fromarea=False,
                                                    isaddress=True,
                                                    rank_address=10,
                                                    distance=0.0),
                                   napi.AddressLine(place_id=33,
                                                    osm_object=None,
                                                    category=('place', 'county'),
                                                    names={'name': 'Hello'},
                                                    extratags=None,
                                                    admin_level=5,
                                                    fromarea=False,
                                                    isaddress=True,
                                                    rank_address=10,
                                                    distance=0.0)
                                 ]))

    reverse.localize(napi.Locales())

    raw = api_impl.format_result(napi.ReverseResults([reverse]), 'geocodejson',
                                 {'addressdetails': True})

    props = json.loads(raw)['features'][0]['properties']['geocoding']
    assert props['housenumber'] == '1'
    assert props['postcode'] == '99446'
    assert 'county' not in props


@pytest.mark.parametrize('fmt', FORMATS)
def test_format_reverse_with_address_none(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 address_rows=napi.AddressLines())

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                 {'addressdetails': True})


    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.find('addressparts') is None
    else:
        result = json.loads(raw)
        assert isinstance(result, dict)

        if fmt == 'geocodejson':
            props = result['features'][0]['properties']['geocoding']
            print(props)
            assert 'admin' in props
        else:
            if fmt == 'geojson':
                props = result['features'][0]['properties']
            else:
                props = result
            assert 'address' in props


@pytest.mark.parametrize('fmt', ['json', 'jsonv2', 'geojson', 'xml'])
def test_format_reverse_with_extratags(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 extratags={'one': 'A', 'two':'B'})

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                 {'extratags': True})

    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.find('extratags').find('tag').attrib['key'] == 'one'
    else:
        result = json.loads(raw)
        if fmt == 'geojson':
            extra = result['features'][0]['properties']['extratags']
        else:
            extra = result['extratags']

        assert extra == {'one': 'A', 'two':'B'}


@pytest.mark.parametrize('fmt', ['json', 'jsonv2', 'geojson', 'xml'])
def test_format_reverse_with_extratags_none(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0))

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                 {'extratags': True})

    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.find('extratags') is not None
    else:
        result = json.loads(raw)
        if fmt == 'geojson':
            extra = result['features'][0]['properties']['extratags']
        else:
            extra = result['extratags']

        assert extra is None


@pytest.mark.parametrize('fmt', ['json', 'jsonv2', 'geojson', 'xml'])
def test_format_reverse_with_namedetails_with_name(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 names={'name': 'A', 'ref':'1'})

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                 {'namedetails': True})

    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.find('namedetails').find('name').text == 'A'
    else:
        result = json.loads(raw)
        if fmt == 'geojson':
            extra = result['features'][0]['properties']['namedetails']
        else:
            extra = result['namedetails']

        assert extra == {'name': 'A', 'ref':'1'}


@pytest.mark.parametrize('fmt', ['json', 'jsonv2', 'geojson', 'xml'])
def test_format_reverse_with_namedetails_without_name(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0))

    raw = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                 {'namedetails': True})

    if fmt == 'xml':
        root = ET.fromstring(raw)
        assert root.find('namedetails') is not None
    else:
        result = json.loads(raw)
        if fmt == 'geojson':
            extra = result['features'][0]['properties']['namedetails']
        else:
            extra = result['namedetails']

        assert extra is None


@pytest.mark.parametrize('fmt', ['json', 'jsonv2'])
def test_search_details_with_icon_available(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('amenity', 'restaurant'),
                                 napi.Point(1.0, 2.0))

    result = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                    {'icon_base_url': 'foo'})

    js = json.loads(result)

    assert js['icon'] == 'foo/food_restaurant.p.20.png'


@pytest.mark.parametrize('fmt', ['json', 'jsonv2'])
def test_search_details_with_icon_not_available(fmt):
    reverse = napi.ReverseResult(napi.SourceTable.PLACEX,
                                 ('amenity', 'tree'),
                                 napi.Point(1.0, 2.0))

    result = api_impl.format_result(napi.ReverseResults([reverse]), fmt,
                                    {'icon_base_url': 'foo'})

    assert 'icon' not in json.loads(result)

