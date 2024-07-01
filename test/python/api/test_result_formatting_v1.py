# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for formatting results for the V1 API.

These test only ensure that the Python code is correct.
For functional tests see BDD test suite.
"""
import datetime as dt
import json

import pytest

import nominatim_api.v1 as api_impl
import nominatim_api as napi

STATUS_FORMATS = {'text', 'json'}

# StatusResult

def test_status_format_list():
    assert set(api_impl.list_formats(napi.StatusResult)) == STATUS_FORMATS


@pytest.mark.parametrize('fmt', list(STATUS_FORMATS))
def test_status_supported(fmt):
    assert api_impl.supports_format(napi.StatusResult, fmt)


def test_status_unsupported():
    assert not api_impl.supports_format(napi.StatusResult, 'gagaga')


def test_status_format_text():
    assert api_impl.format_result(napi.StatusResult(0, 'message here'), 'text', {}) == 'OK'


def test_status_format_text():
    assert api_impl.format_result(napi.StatusResult(500, 'message here'), 'text', {}) == 'ERROR: message here'


def test_status_format_json_minimal():
    status = napi.StatusResult(700, 'Bad format.')

    result = api_impl.format_result(status, 'json', {})

    assert result == \
           f'{{"status":700,"message":"Bad format.","software_version":"{napi.__version__}"}}'


def test_status_format_json_full():
    status = napi.StatusResult(0, 'OK')
    status.data_updated = dt.datetime(2010, 2, 7, 20, 20, 3, 0, tzinfo=dt.timezone.utc)
    status.database_version = '5.6'

    result = api_impl.format_result(status, 'json', {})

    assert result == \
           f'{{"status":0,"message":"OK","data_updated":"2010-02-07T20:20:03+00:00","software_version":"{napi.__version__}","database_version":"5.6"}}'


# DetailedResult

def test_search_details_minimal():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0))

    result = api_impl.format_result(search, 'json', {})

    assert json.loads(result) == \
           {'category': 'place',
            'type': 'thing',
            'admin_level': 15,
            'names': {},
            'localname': '',
            'calculated_importance': pytest.approx(0.00001),
            'rank_address': 30,
            'rank_search': 30,
            'isarea': False,
            'addresstags': {},
            'extratags': {},
            'centroid': {'type': 'Point', 'coordinates': [1.0, 2.0]},
            'geometry': {'type': 'Point', 'coordinates': [1.0, 2.0]},
           }


def test_search_details_full():
    import_date = dt.datetime(2010, 2, 7, 20, 20, 3, 0, tzinfo=dt.timezone.utc)
    search = napi.DetailedResult(
                  source_table=napi.SourceTable.PLACEX,
                  category=('amenity', 'bank'),
                  centroid=napi.Point(56.947, -87.44),
                  place_id=37563,
                  parent_place_id=114,
                  linked_place_id=55693,
                  osm_object=('W', 442100),
                  admin_level=14,
                  names={'name': 'Bank', 'name:fr': 'Banque'},
                  address={'city': 'Niento', 'housenumber': '  3'},
                  extratags={'atm': 'yes'},
                  housenumber='3',
                  postcode='556 X23',
                  wikipedia='en:Bank',
                  rank_address=29,
                  rank_search=28,
                  importance=0.0443,
                  country_code='ll',
                  indexed_date = import_date
                  )
    search.localize(napi.Locales())

    result = api_impl.format_result(search, 'json', {})

    assert json.loads(result) == \
           {'place_id': 37563,
            'parent_place_id': 114,
            'osm_type': 'W',
            'osm_id': 442100,
            'category': 'amenity',
            'type': 'bank',
            'admin_level': 14,
            'localname': 'Bank',
            'names': {'name': 'Bank', 'name:fr': 'Banque'},
            'addresstags': {'city': 'Niento', 'housenumber': '  3'},
            'housenumber': '3',
            'calculated_postcode': '556 X23',
            'country_code': 'll',
            'indexed_date': '2010-02-07T20:20:03+00:00',
            'importance': pytest.approx(0.0443),
            'calculated_importance': pytest.approx(0.0443),
            'extratags': {'atm': 'yes'},
            'calculated_wikipedia': 'en:Bank',
            'rank_address': 29,
            'rank_search': 28,
            'isarea': False,
            'centroid': {'type': 'Point', 'coordinates': [56.947, -87.44]},
            'geometry': {'type': 'Point', 'coordinates': [56.947, -87.44]},
           }


@pytest.mark.parametrize('gtype,isarea', [('ST_Point', False),
                                          ('ST_LineString', False),
                                          ('ST_Polygon', True),
                                          ('ST_MultiPolygon', True)])
def test_search_details_no_geometry(gtype, isarea):
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                               ('place', 'thing'),
                               napi.Point(1.0, 2.0),
                               geometry={'type': gtype})

    result = api_impl.format_result(search, 'json', {})
    js = json.loads(result)

    assert js['geometry'] == {'type': 'Point', 'coordinates': [1.0, 2.0]}
    assert js['isarea'] == isarea


def test_search_details_with_geometry():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 geometry={'geojson': '{"type":"Point","coordinates":[56.947,-87.44]}'})

    result = api_impl.format_result(search, 'json', {})
    js = json.loads(result)

    assert js['geometry'] == {'type': 'Point', 'coordinates': [56.947, -87.44]}
    assert js['isarea'] == False


def test_search_details_with_icon_available():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('amenity', 'restaurant'),
                                 napi.Point(1.0, 2.0))

    result = api_impl.format_result(search, 'json', {'icon_base_url': 'foo'})
    js = json.loads(result)

    assert js['icon'] == 'foo/food_restaurant.p.20.png'


def test_search_details_with_icon_not_available():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('amenity', 'tree'),
                                 napi.Point(1.0, 2.0))

    result = api_impl.format_result(search, 'json', {'icon_base_url': 'foo'})
    js = json.loads(result)

    assert 'icon' not in js


def test_search_details_with_address_minimal():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 address_rows=[
                                   napi.AddressLine(place_id=None,
                                                    osm_object=None,
                                                    category=('bnd', 'note'),
                                                    names={},
                                                    extratags=None,
                                                    admin_level=None,
                                                    fromarea=False,
                                                    isaddress=False,
                                                    rank_address=10,
                                                    distance=0.0)
                                 ])

    result = api_impl.format_result(search, 'json', {})
    js = json.loads(result)

    assert js['address'] == [{'localname': '',
                              'class': 'bnd',
                              'type': 'note',
                              'rank_address': 10,
                              'distance': 0.0,
                              'isaddress': False}]


@pytest.mark.parametrize('field,outfield', [('address_rows', 'address'),
                                            ('linked_rows', 'linked_places'),
                                            ('parented_rows', 'hierarchy')
                                           ])
def test_search_details_with_further_infos(field, outfield):
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0))

    setattr(search, field, [napi.AddressLine(place_id=3498,
                                             osm_object=('R', 442),
                                             category=('bnd', 'note'),
                                             names={'name': 'Trespass'},
                                             extratags={'access': 'no',
                                                        'place_type': 'spec'},
                                             admin_level=4,
                                             fromarea=True,
                                             isaddress=True,
                                             rank_address=10,
                                             distance=0.034)
                            ])

    result = api_impl.format_result(search, 'json', {})
    js = json.loads(result)

    assert js[outfield] == [{'localname': 'Trespass',
                              'place_id': 3498,
                              'osm_id': 442,
                              'osm_type': 'R',
                              'place_type': 'spec',
                              'class': 'bnd',
                              'type': 'note',
                              'admin_level': 4,
                              'rank_address': 10,
                              'distance': 0.034,
                              'isaddress': True}]


def test_search_details_grouped_hierarchy():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 parented_rows =
                                     [napi.AddressLine(place_id=3498,
                                             osm_object=('R', 442),
                                             category=('bnd', 'note'),
                                             names={'name': 'Trespass'},
                                             extratags={'access': 'no',
                                                        'place_type': 'spec'},
                                             admin_level=4,
                                             fromarea=True,
                                             isaddress=True,
                                             rank_address=10,
                                             distance=0.034)
                                     ])

    result = api_impl.format_result(search, 'json', {'group_hierarchy': True})
    js = json.loads(result)

    assert js['hierarchy'] == {'note': [{'localname': 'Trespass',
                              'place_id': 3498,
                              'osm_id': 442,
                              'osm_type': 'R',
                              'place_type': 'spec',
                              'class': 'bnd',
                              'type': 'note',
                              'admin_level': 4,
                              'rank_address': 10,
                              'distance': 0.034,
                              'isaddress': True}]}


def test_search_details_keywords_name():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 name_keywords=[
                                     napi.WordInfo(23, 'foo', 'mefoo'),
                                     napi.WordInfo(24, 'foo', 'bafoo')])

    result = api_impl.format_result(search, 'json', {'keywords': True})
    js = json.loads(result)

    assert js['keywords'] == {'name': [{'id': 23, 'token': 'foo'},
                                      {'id': 24, 'token': 'foo'}],
                              'address': []}


def test_search_details_keywords_address():
    search = napi.DetailedResult(napi.SourceTable.PLACEX,
                                 ('place', 'thing'),
                                 napi.Point(1.0, 2.0),
                                 address_keywords=[
                                     napi.WordInfo(23, 'foo', 'mefoo'),
                                     napi.WordInfo(24, 'foo', 'bafoo')])

    result = api_impl.format_result(search, 'json', {'keywords': True})
    js = json.loads(result)

    assert js['keywords'] == {'address': [{'id': 23, 'token': 'foo'},
                                      {'id': 24, 'token': 'foo'}],
                              'name': []}

