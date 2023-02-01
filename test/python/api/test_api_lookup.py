# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for lookup API call.
"""
import datetime as dt

import pytest

import nominatim.api as napi

@pytest.mark.parametrize('idobj', (napi.PlaceID(332), napi.OsmID('W', 4),
                                   napi.OsmID('W', 4, 'highway')))
def test_lookup_in_placex(apiobj, idobj):
    import_date = dt.datetime(2022, 12, 7, 14, 14, 46, 0)
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',
                     name={'name': 'Road'}, address={'city': 'Barrow'},
                     extratags={'surface': 'paved'},
                     parent_place_id=34, linked_place_id=55,
                     admin_level=15, country_code='gb',
                     housenumber='4',
                     postcode='34425', wikipedia='en:Faa',
                     rank_search=27, rank_address=26,
                     importance=0.01,
                     centroid=(23, 34),
                     indexed_date=import_date,
                     geometry='LINESTRING(23 34, 23.1 34, 23.1 34.1, 23 34)')

    result = apiobj.api.lookup(idobj, napi.LookupDetails())

    assert result is not None

    assert result.source_table.name == 'PLACEX'
    assert result.category == ('highway', 'residential')
    assert result.centroid == (pytest.approx(23.0), pytest.approx(34.0))

    assert result.place_id == 332
    assert result.parent_place_id == 34
    assert result.linked_place_id == 55
    assert result.osm_object == ('W', 4)
    assert result.admin_level == 15

    assert result.names == {'name': 'Road'}
    assert result.address == {'city': 'Barrow'}
    assert result.extratags == {'surface': 'paved'}

    assert result.housenumber == '4'
    assert result.postcode == '34425'
    assert result.wikipedia == 'en:Faa'

    assert result.rank_search == 27
    assert result.rank_address == 26
    assert result.importance == pytest.approx(0.01)

    assert result.country_code == 'gb'
    assert result.indexed_date == import_date

    assert result.address_rows is None
    assert result.linked_rows is None
    assert result.parented_rows is None
    assert result.name_keywords is None
    assert result.address_keywords is None

    assert result.geometry == {'type': 'ST_LineString'}


def test_lookup_in_placex_minimal_info(apiobj):
    import_date = dt.datetime(2022, 12, 7, 14, 14, 46, 0)
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',
                     admin_level=15,
                     rank_search=27, rank_address=26,
                     centroid=(23, 34),
                     indexed_date=import_date,
                     geometry='LINESTRING(23 34, 23.1 34, 23.1 34.1, 23 34)')

    result = apiobj.api.lookup(napi.PlaceID(332), napi.LookupDetails())

    assert result is not None

    assert result.source_table.name == 'PLACEX'
    assert result.category == ('highway', 'residential')
    assert result.centroid == (pytest.approx(23.0), pytest.approx(34.0))

    assert result.place_id == 332
    assert result.parent_place_id is None
    assert result.linked_place_id is None
    assert result.osm_object == ('W', 4)
    assert result.admin_level == 15

    assert result.names is None
    assert result.address is None
    assert result.extratags is None

    assert result.housenumber is None
    assert result.postcode is None
    assert result.wikipedia is None

    assert result.rank_search == 27
    assert result.rank_address == 26
    assert result.importance is None

    assert result.country_code is None
    assert result.indexed_date == import_date

    assert result.address_rows is None
    assert result.linked_rows is None
    assert result.parented_rows is None
    assert result.name_keywords is None
    assert result.address_keywords is None

    assert result.geometry == {'type': 'ST_LineString'}


def test_lookup_in_placex_with_geometry(apiobj):
    apiobj.add_placex(place_id=332,
                      geometry='LINESTRING(23 34, 23.1 34)')

    result = apiobj.api.lookup(napi.PlaceID(332),
                               napi.LookupDetails(geometry_output=napi.GeometryFormat.GEOJSON))

    assert result.geometry == {'geojson': '{"type":"LineString","coordinates":[[23,34],[23.1,34]]}'}


def test_lookup_placex_with_address_details(apiobj):
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl',
                     rank_search=27, rank_address=26)
    apiobj.add_address_placex(332, fromarea=False, isaddress=False,
                              distance=0.0034,
                              place_id=1000, osm_type='N', osm_id=3333,
                              class_='place', type='suburb', name='Smallplace',
                              country_code='pl', admin_level=13,
                              rank_search=24, rank_address=23)
    apiobj.add_address_placex(332, fromarea=True, isaddress=True,
                              place_id=1001, osm_type='N', osm_id=3334,
                              class_='place', type='city', name='Bigplace',
                              country_code='pl',
                              rank_search=17, rank_address=16)

    result = apiobj.api.lookup(napi.PlaceID(332),
                               napi.LookupDetails(address_details=True))

    assert result.address_rows == [
               napi.AddressLine(place_id=332, osm_object=('W', 4),
                                category=('highway', 'residential'),
                                names={'name': 'Street'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=26, distance=0.0),
               napi.AddressLine(place_id=1000, osm_object=('N', 3333),
                                category=('place', 'suburb'),
                                names={'name': 'Smallplace'}, extratags={},
                                admin_level=13, fromarea=False, isaddress=True,
                                rank_address=23, distance=0.0034),
               napi.AddressLine(place_id=1001, osm_object=('N', 3334),
                                category=('place', 'city'),
                                names={'name': 'Bigplace'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=16, distance=0.0),
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'country_code'),
                                names={'ref': 'pl'}, extratags={},
                                admin_level=None, fromarea=True, isaddress=False,
                                rank_address=4, distance=0.0)

           ]


def test_lookup_place_wth_linked_places_none_existing(apiobj):
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', linked_place_id=45,
                     rank_search=27, rank_address=26)

    result = apiobj.api.lookup(napi.PlaceID(332),
                               napi.LookupDetails(linked_places=True))

    assert result.linked_rows == []


def test_lookup_place_with_linked_places_existing(apiobj):
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', linked_place_id=45,
                     rank_search=27, rank_address=26)
    apiobj.add_placex(place_id=1001, osm_type='W', osm_id=5,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', linked_place_id=332,
                     rank_search=27, rank_address=26)
    apiobj.add_placex(place_id=1002, osm_type='W', osm_id=6,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', linked_place_id=332,
                     rank_search=27, rank_address=26)

    result = apiobj.api.lookup(napi.PlaceID(332),
                               napi.LookupDetails(linked_places=True))

    assert result.linked_rows == [
               napi.AddressLine(place_id=1001, osm_object=('W', 5),
                                category=('highway', 'residential'),
                                names={'name': 'Street'}, extratags={},
                                admin_level=15, fromarea=False, isaddress=True,
                                rank_address=26, distance=0.0),
               napi.AddressLine(place_id=1002, osm_object=('W', 6),
                                category=('highway', 'residential'),
                                names={'name': 'Street'}, extratags={},
                                admin_level=15, fromarea=False, isaddress=True,
                                rank_address=26, distance=0.0),
    ]


def test_lookup_place_with_parented_places_not_existing(apiobj):
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', parent_place_id=45,
                     rank_search=27, rank_address=26)

    result = apiobj.api.lookup(napi.PlaceID(332),
                               napi.LookupDetails(parented_places=True))

    assert result.parented_rows == []


def test_lookup_place_with_parented_places_existing(apiobj):
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', parent_place_id=45,
                     rank_search=27, rank_address=26)
    apiobj.add_placex(place_id=1001, osm_type='N', osm_id=5,
                     class_='place', type='house', housenumber='23',
                     country_code='pl', parent_place_id=332,
                     rank_search=30, rank_address=30)
    apiobj.add_placex(place_id=1002, osm_type='W', osm_id=6,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', parent_place_id=332,
                     rank_search=27, rank_address=26)

    result = apiobj.api.lookup(napi.PlaceID(332),
                               napi.LookupDetails(parented_places=True))

    assert result.parented_rows == [
               napi.AddressLine(place_id=1001, osm_object=('N', 5),
                                category=('place', 'house'),
                                names={'housenumber': '23'}, extratags={},
                                admin_level=15, fromarea=False, isaddress=True,
                                rank_address=30, distance=0.0),
    ]


@pytest.mark.parametrize('gtype', (napi.GeometryFormat.KML,
                                    napi.GeometryFormat.SVG,
                                    napi.GeometryFormat.TEXT))
def test_lookup_unsupported_geometry(apiobj, gtype):
    apiobj.add_placex(place_id=332)

    with pytest.raises(ValueError):
        apiobj.api.lookup(napi.PlaceID(332),
                          napi.LookupDetails(geometry_output=gtype))
