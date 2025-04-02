# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for reverse API call.

These tests make sure that all Python code is correct and executable.
Functional tests can be found in the BDD test suite.
"""
import json

import pytest

import nominatim_api as napi

API_OPTIONS = {'reverse'}


def test_reverse_rank_30(apiobj, frontend):
    apiobj.add_placex(place_id=223, class_='place', type='house',
                      housenumber='1',
                      centroid=(1.3, 0.7),
                      geometry='POINT(1.3 0.7)')

    api = frontend(apiobj, options=API_OPTIONS)
    result = api.reverse((1.3, 0.7))

    assert result is not None
    assert result.place_id == 223


@pytest.mark.parametrize('country', ['de', 'us'])
def test_reverse_street(apiobj, frontend, country):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(10.0, 10.0),
                      country_code=country,
                      geometry='LINESTRING(9.995 10, 10.005 10)')

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((9.995, 10)).place_id == 990


def test_reverse_ignore_unindexed(apiobj, frontend):
    apiobj.add_placex(place_id=223, class_='place', type='house',
                      housenumber='1',
                      indexed_status=2,
                      centroid=(1.3, 0.7),
                      geometry='POINT(1.3 0.7)')

    api = frontend(apiobj, options=API_OPTIONS)
    result = api.reverse((1.3, 0.7))

    assert result is None


@pytest.mark.parametrize('y,layer,place_id',
                         [(0.7, napi.DataLayer.ADDRESS, 223),
                          (0.70001, napi.DataLayer.POI, 224),
                          (0.7, napi.DataLayer.ADDRESS | napi.DataLayer.POI, 224),
                          (0.70001, napi.DataLayer.ADDRESS | napi.DataLayer.POI, 223),
                          (0.7, napi.DataLayer.MANMADE, 225),
                          (0.7, napi.DataLayer.RAILWAY, 226),
                          (0.7, napi.DataLayer.NATURAL, 227),
                          (0.70003, napi.DataLayer.MANMADE | napi.DataLayer.RAILWAY, 225),
                          (0.70003, napi.DataLayer.MANMADE | napi.DataLayer.NATURAL, 225),
                          (5, napi.DataLayer.ADDRESS, 229),
                          (5.0001, napi.DataLayer.ADDRESS, 229)])
def test_reverse_rank_30_layers(apiobj, frontend, y, layer, place_id):
    apiobj.add_placex(place_id=223, osm_type='N', class_='place', type='house',
                      housenumber='1',
                      rank_address=30,
                      rank_search=30,
                      centroid=(1.3, 0.70001))
    apiobj.add_placex(place_id=224, osm_type='N', class_='amenity', type='toilet',
                      rank_address=30,
                      rank_search=30,
                      centroid=(1.3, 0.7))
    apiobj.add_placex(place_id=225, osm_type='N', class_='man_made', type='tower',
                      rank_address=0,
                      rank_search=30,
                      centroid=(1.3, 0.70003))
    apiobj.add_placex(place_id=226, osm_type='N', class_='railway', type='station',
                      rank_address=0,
                      rank_search=30,
                      centroid=(1.3, 0.70004))
    apiobj.add_placex(place_id=227, osm_type='N', class_='natural', type='cave',
                      rank_address=0,
                      rank_search=30,
                      centroid=(1.3, 0.70005))
    apiobj.add_placex(place_id=229, class_='place', type='house',
                      name={'addr:housename': 'Old Cottage'},
                      rank_address=30,
                      rank_search=30,
                      centroid=(1.3, 5))
    apiobj.add_placex(place_id=230, class_='place', type='house',
                      housenumber='2',
                      address={'_inherited': ''},
                      rank_address=30,
                      rank_search=30,
                      centroid=(1.3, 5.0001))

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((1.3, y), layers=layer).place_id == place_id


def test_reverse_poi_layer_with_no_pois(apiobj, frontend):
    apiobj.add_placex(place_id=223, class_='place', type='house',
                      housenumber='1',
                      rank_address=30,
                      rank_search=30,
                      centroid=(1.3, 0.70001))

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((1.3, 0.70001), max_rank=29,
                       layers=napi.DataLayer.POI) is None


@pytest.mark.parametrize('with_geom', [True, False])
def test_reverse_housenumber_on_street(apiobj, frontend, with_geom):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(10.0, 10.0),
                      geometry='LINESTRING(9.995 10, 10.005 10)')
    apiobj.add_placex(place_id=991, class_='place', type='house',
                      parent_place_id=990,
                      rank_search=30, rank_address=30,
                      housenumber='23',
                      centroid=(10.0, 10.00001))
    apiobj.add_placex(place_id=1990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'Other Street'},
                      centroid=(10.0, 1.0),
                      geometry='LINESTRING(9.995 1, 10.005 1)')
    apiobj.add_placex(place_id=1991, class_='place', type='house',
                      parent_place_id=1990,
                      rank_search=30, rank_address=30,
                      housenumber='23',
                      centroid=(10.0, 1.00001))

    params = {'geometry_output': napi.GeometryFormat.TEXT} if with_geom else {}

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((10.0, 10.0), max_rank=30, **params).place_id == 991
    assert api.reverse((10.0, 10.0), max_rank=27).place_id == 990
    assert api.reverse((10.0, 10.00001), max_rank=30).place_id == 991
    assert api.reverse((10.0, 1.0), **params).place_id == 1991


@pytest.mark.parametrize('with_geom', [True, False])
def test_reverse_housenumber_interpolation(apiobj, frontend, with_geom):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(10.0, 10.0),
                      geometry='LINESTRING(9.995 10, 10.005 10)')
    apiobj.add_placex(place_id=991, class_='place', type='house',
                      parent_place_id=990,
                      rank_search=30, rank_address=30,
                      housenumber='23',
                      centroid=(10.0, 10.00002))
    apiobj.add_osmline(place_id=992,
                       parent_place_id=990,
                       startnumber=1, endnumber=3, step=1,
                       centroid=(10.0, 10.00001),
                       geometry='LINESTRING(9.995 10.00001, 10.005 10.00001)')
    apiobj.add_placex(place_id=1990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'Other Street'},
                      centroid=(10.0, 20.0),
                      geometry='LINESTRING(9.995 20, 10.005 20)')
    apiobj.add_osmline(place_id=1992,
                       parent_place_id=1990,
                       startnumber=1, endnumber=3, step=1,
                       centroid=(10.0, 20.00001),
                       geometry='LINESTRING(9.995 20.00001, 10.005 20.00001)')

    params = {'geometry_output': napi.GeometryFormat.TEXT} if with_geom else {}

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((10.0, 10.0), **params).place_id == 992
    assert api.reverse((10.0, 20.0), **params).place_id == 1992


def test_reverse_housenumber_point_interpolation(apiobj, frontend):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(10.0, 10.0),
                      geometry='LINESTRING(9.995 10, 10.005 10)')
    apiobj.add_osmline(place_id=992,
                       parent_place_id=990,
                       startnumber=42, endnumber=42, step=1,
                       centroid=(10.0, 10.00001),
                       geometry='POINT(10.0 10.00001)')

    api = frontend(apiobj, options=API_OPTIONS)
    res = api.reverse((10.0, 10.0))
    assert res.place_id == 992
    assert res.housenumber == '42'


def test_reverse_tiger_number(apiobj, frontend):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(10.0, 10.0),
                      country_code='us',
                      geometry='LINESTRING(9.995 10, 10.005 10)')
    apiobj.add_tiger(place_id=992,
                     parent_place_id=990,
                     startnumber=1, endnumber=3, step=1,
                     centroid=(10.0, 10.00001),
                     geometry='LINESTRING(9.995 10.00001, 10.005 10.00001)')

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((10.0, 10.0)).place_id == 992
    assert api.reverse((10.0, 10.00001)).place_id == 992


def test_reverse_point_tiger(apiobj, frontend):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(10.0, 10.0),
                      country_code='us',
                      geometry='LINESTRING(9.995 10, 10.005 10)')
    apiobj.add_tiger(place_id=992,
                     parent_place_id=990,
                     startnumber=1, endnumber=1, step=1,
                     centroid=(10.0, 10.00001),
                     geometry='POINT(10.0 10.00001)')

    api = frontend(apiobj, options=API_OPTIONS)
    res = api.reverse((10.0, 10.0))
    assert res.place_id == 992
    assert res.housenumber == '1'


def test_reverse_low_zoom_address(apiobj, frontend):
    apiobj.add_placex(place_id=1001, class_='place', type='house',
                      housenumber='1',
                      rank_address=30,
                      rank_search=30,
                      centroid=(59.3, 80.70001))
    apiobj.add_placex(place_id=1002, class_='place', type='town',
                      name={'name': 'Town'},
                      rank_address=16,
                      rank_search=16,
                      centroid=(59.3, 80.70001),
                      geometry="""POLYGON((59.3 80.70001, 59.3001 80.70001,
                                        59.3001 80.70101, 59.3 80.70101, 59.3 80.70001))""")

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((59.30005, 80.7005)).place_id == 1001
    assert api.reverse((59.30005, 80.7005), max_rank=18).place_id == 1002


def test_reverse_place_node_in_area(apiobj, frontend):
    apiobj.add_placex(place_id=1002, class_='place', type='town',
                      name={'name': 'Town Area'},
                      rank_address=16,
                      rank_search=16,
                      centroid=(59.3, 80.70001),
                      geometry="""POLYGON((59.3 80.70001, 59.3001 80.70001,
                                        59.3001 80.70101, 59.3 80.70101, 59.3 80.70001))""")
    apiobj.add_placex(place_id=1003, class_='place', type='suburb',
                      name={'name': 'Suburb Point'},
                      osm_type='N',
                      rank_address=18,
                      rank_search=18,
                      centroid=(59.30004, 80.70055))

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((59.30004, 80.70055)).place_id == 1003


@pytest.mark.parametrize('layer,place_id', [(napi.DataLayer.MANMADE, 225),
                                            (napi.DataLayer.RAILWAY, 226),
                                            (napi.DataLayer.NATURAL, 227),
                                            (napi.DataLayer.MANMADE | napi.DataLayer.RAILWAY, 225),
                                            (napi.DataLayer.MANMADE | napi.DataLayer.NATURAL, 225)])
def test_reverse_larger_area_layers(apiobj, frontend, layer, place_id):
    apiobj.add_placex(place_id=225, class_='man_made', type='dam',
                      name={'name': 'Dam'},
                      rank_address=0,
                      rank_search=25,
                      centroid=(1.3, 0.70003))
    apiobj.add_placex(place_id=226, class_='railway', type='yard',
                      name={'name': 'Dam'},
                      rank_address=0,
                      rank_search=20,
                      centroid=(1.3, 0.70004))
    apiobj.add_placex(place_id=227, class_='natural', type='spring',
                      name={'name': 'Dam'},
                      rank_address=0,
                      rank_search=16,
                      centroid=(1.3, 0.70005))

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((1.3, 0.7), layers=layer).place_id == place_id


def test_reverse_country_lookup_no_objects(apiobj, frontend):
    apiobj.add_country('xx', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((0.5, 0.5)) is None


@pytest.mark.parametrize('rank', [4, 30])
@pytest.mark.parametrize('with_geom', [True, False])
def test_reverse_country_lookup_country_only(apiobj, frontend, rank, with_geom):
    apiobj.add_country('xx', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
    apiobj.add_country('yy', 'POLYGON((10 0, 10 1, 11 1, 11 0, 10 0))')
    apiobj.add_placex(place_id=225, class_='place', type='country',
                      name={'name': 'My Country'},
                      rank_address=4,
                      rank_search=4,
                      country_code='xx',
                      centroid=(0.7, 0.7))

    params = {'max_rank': rank}
    if with_geom:
        params['geometry_output'] = napi.GeometryFormat.TEXT

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((0.5, 0.5), **params).place_id == 225
    assert api.reverse((10.5, 0.5), **params) is None


@pytest.mark.parametrize('with_geom', [True, False])
def test_reverse_country_lookup_place_node_inside(apiobj, frontend, with_geom):
    apiobj.add_country('xx', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
    apiobj.add_country('yy', 'POLYGON((10 0, 10 1, 11 1, 11 0, 10 0))')
    apiobj.add_placex(place_id=225, class_='place', type='state',
                      osm_type='N',
                      name={'name': 'My State'},
                      rank_address=6,
                      rank_search=6,
                      country_code='xx',
                      centroid=(0.5, 0.505))
    apiobj.add_placex(place_id=425, class_='place', type='state',
                      osm_type='N',
                      name={'name': 'Other State'},
                      rank_address=6,
                      rank_search=6,
                      country_code='yy',
                      centroid=(10.5, 0.505))

    params = {'geometry_output': napi.GeometryFormat.KML} if with_geom else {}

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((0.5, 0.5), **params).place_id == 225
    assert api.reverse((10.5, 0.5), **params).place_id == 425


@pytest.mark.parametrize('gtype', list(napi.GeometryFormat))
def test_reverse_geometry_output_placex(apiobj, frontend, gtype):
    apiobj.add_country('xx', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
    apiobj.add_placex(place_id=1001, class_='place', type='house',
                      housenumber='1',
                      rank_address=30,
                      rank_search=30,
                      centroid=(59.3, 80.70001))
    apiobj.add_placex(place_id=1003, class_='place', type='suburb',
                      name={'name': 'Suburb Point'},
                      osm_type='N',
                      rank_address=18,
                      rank_search=18,
                      country_code='xx',
                      centroid=(0.5, 0.5))

    api = frontend(apiobj, options=API_OPTIONS)
    assert api.reverse((59.3, 80.70001), geometry_output=gtype).place_id == 1001
    assert api.reverse((0.5, 0.5), geometry_output=gtype).place_id == 1003


def test_reverse_simplified_geometry(apiobj, frontend):
    apiobj.add_placex(place_id=1001, class_='place', type='house',
                      housenumber='1',
                      rank_address=30,
                      rank_search=30,
                      centroid=(59.3, 80.70001))

    api = frontend(apiobj, options=API_OPTIONS)
    details = dict(geometry_output=napi.GeometryFormat.GEOJSON,
                   geometry_simplification=0.1)
    assert api.reverse((59.3, 80.70001), **details).place_id == 1001


def test_reverse_interpolation_geometry(apiobj, frontend):
    apiobj.add_osmline(place_id=992,
                       parent_place_id=990,
                       startnumber=1, endnumber=3, step=1,
                       centroid=(10.0, 10.00001),
                       geometry='LINESTRING(9.995 10.00001, 10.005 10.00001)')

    api = frontend(apiobj, options=API_OPTIONS)
    result = api.reverse((10.0, 10.0), geometry_output=napi.GeometryFormat.TEXT)

    assert result.geometry['text'] == 'POINT(10 10.00001)'


def test_reverse_tiger_geometry(apiobj, frontend):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(10.0, 10.0),
                      country_code='us',
                      geometry='LINESTRING(9.995 10, 10.005 10)')
    apiobj.add_tiger(place_id=992,
                     parent_place_id=990,
                     startnumber=1, endnumber=3, step=1,
                     centroid=(10.0, 10.00001),
                     geometry='LINESTRING(9.995 10.00001, 10.005 10.00001)')
    apiobj.add_placex(place_id=1000, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      name={'name': 'My Street'},
                      centroid=(11.0, 11.0),
                      country_code='us',
                      geometry='LINESTRING(10.995 11, 11.005 11)')
    apiobj.add_tiger(place_id=1001,
                     parent_place_id=1000,
                     startnumber=1, endnumber=3, step=1,
                     centroid=(11.0, 11.00001),
                     geometry='LINESTRING(10.995 11.00001, 11.005 11.00001)')

    api = frontend(apiobj, options=API_OPTIONS)

    params = {'geometry_output': napi.GeometryFormat.GEOJSON}

    output = api.reverse((10.0, 10.0), **params)
    assert json.loads(output.geometry['geojson']) \
        == {'coordinates': [10, 10.00001], 'type': 'Point'}

    output = api.reverse((11.0, 11.0), **params)
    assert json.loads(output.geometry['geojson']) \
        == {'coordinates': [11, 11.00001], 'type': 'Point'}
