# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for details API call.
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

    result = apiobj.api.details(idobj)

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
    assert result.indexed_date == import_date.replace(tzinfo=dt.timezone.utc)

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

    result = apiobj.api.details(napi.PlaceID(332))

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
    assert result.indexed_date == import_date.replace(tzinfo=dt.timezone.utc)

    assert result.address_rows is None
    assert result.linked_rows is None
    assert result.parented_rows is None
    assert result.name_keywords is None
    assert result.address_keywords is None

    assert result.geometry == {'type': 'ST_LineString'}


def test_lookup_in_placex_with_geometry(apiobj):
    apiobj.add_placex(place_id=332,
                      geometry='LINESTRING(23 34, 23.1 34)')

    result = apiobj.api.details(napi.PlaceID(332), geometry_output=napi.GeometryFormat.GEOJSON)

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

    result = apiobj.api.details(napi.PlaceID(332), address_details=True)

    assert result.address_rows == [
               napi.AddressLine(place_id=332, osm_object=('W', 4),
                                category=('highway', 'residential'),
                                names={'name': 'Street'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=26, distance=0.0,
                                local_name='Street'),
               napi.AddressLine(place_id=1000, osm_object=('N', 3333),
                                category=('place', 'suburb'),
                                names={'name': 'Smallplace'}, extratags={},
                                admin_level=13, fromarea=False, isaddress=True,
                                rank_address=23, distance=0.0034,
                                local_name='Smallplace'),
               napi.AddressLine(place_id=1001, osm_object=('N', 3334),
                                category=('place', 'city'),
                                names={'name': 'Bigplace'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=16, distance=0.0,
                                local_name='Bigplace'),
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'country_code'),
                                names={'ref': 'pl'}, extratags={},
                                admin_level=None, fromarea=True, isaddress=False,
                                rank_address=4, distance=0.0)
           ]


def test_lookup_place_with_linked_places_none_existing(apiobj):
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',  name='Street',
                     country_code='pl', linked_place_id=45,
                     rank_search=27, rank_address=26)

    result = apiobj.api.details(napi.PlaceID(332), linked_places=True)

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

    result = apiobj.api.details(napi.PlaceID(332), linked_places=True)

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

    result = apiobj.api.details(napi.PlaceID(332), parented_places=True)

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

    result = apiobj.api.details(napi.PlaceID(332), parented_places=True)

    assert result.parented_rows == [
               napi.AddressLine(place_id=1001, osm_object=('N', 5),
                                category=('place', 'house'),
                                names={'housenumber': '23'}, extratags={},
                                admin_level=15, fromarea=False, isaddress=True,
                                rank_address=30, distance=0.0),
    ]


@pytest.mark.parametrize('idobj', (napi.PlaceID(4924), napi.OsmID('W', 9928)))
def test_lookup_in_osmline(apiobj, idobj):
    import_date = dt.datetime(2022, 12, 7, 14, 14, 46, 0)
    apiobj.add_osmline(place_id=4924, osm_id=9928,
                       parent_place_id=12,
                       startnumber=1, endnumber=4, step=1,
                       country_code='gb', postcode='34425',
                       address={'city': 'Big'},
                       indexed_date=import_date,
                       geometry='LINESTRING(23 34, 23 35)')

    result = apiobj.api.details(idobj)

    assert result is not None

    assert result.source_table.name == 'OSMLINE'
    assert result.category == ('place', 'houses')
    assert result.centroid == (pytest.approx(23.0), pytest.approx(34.5))

    assert result.place_id == 4924
    assert result.parent_place_id == 12
    assert result.linked_place_id is None
    assert result.osm_object == ('W', 9928)
    assert result.admin_level == 15

    assert result.names is None
    assert result.address == {'city': 'Big'}
    assert result.extratags == {'startnumber': '1', 'endnumber': '4', 'step': '1'}

    assert result.housenumber is None
    assert result.postcode == '34425'
    assert result.wikipedia is None

    assert result.rank_search == 30
    assert result.rank_address == 30
    assert result.importance is None

    assert result.country_code == 'gb'
    assert result.indexed_date == import_date.replace(tzinfo=dt.timezone.utc)

    assert result.address_rows is None
    assert result.linked_rows is None
    assert result.parented_rows is None
    assert result.name_keywords is None
    assert result.address_keywords is None

    assert result.geometry == {'type': 'ST_LineString'}


def test_lookup_in_osmline_split_interpolation(apiobj):
    apiobj.add_osmline(place_id=1000, osm_id=9,
                       startnumber=2, endnumber=4, step=1)
    apiobj.add_osmline(place_id=1001, osm_id=9,
                       startnumber=6, endnumber=9, step=1)
    apiobj.add_osmline(place_id=1002, osm_id=9,
                       startnumber=11, endnumber=20, step=1)

    for i in range(1, 6):
        result = apiobj.api.details(napi.OsmID('W', 9, str(i)))
        assert result.place_id == 1000
    for i in range(7, 11):
        result = apiobj.api.details(napi.OsmID('W', 9, str(i)))
        assert result.place_id == 1001
    for i in range(12, 22):
        result = apiobj.api.details(napi.OsmID('W', 9, str(i)))
        assert result.place_id == 1002


def test_lookup_osmline_with_address_details(apiobj):
    apiobj.add_osmline(place_id=9000, osm_id=9,
                       startnumber=2, endnumber=4, step=1,
                       parent_place_id=332)
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

    result = apiobj.api.details(napi.PlaceID(9000), address_details=True)

    assert result.address_rows == [
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'house_number'),
                                names={'ref': '2'}, extratags={},
                                admin_level=None, fromarea=True, isaddress=True,
                                rank_address=28, distance=0.0,
                                local_name='2'),
               napi.AddressLine(place_id=332, osm_object=('W', 4),
                                category=('highway', 'residential'),
                                names={'name': 'Street'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=26, distance=0.0,
                                local_name='Street'),
               napi.AddressLine(place_id=1000, osm_object=('N', 3333),
                                category=('place', 'suburb'),
                                names={'name': 'Smallplace'}, extratags={},
                                admin_level=13, fromarea=False, isaddress=True,
                                rank_address=23, distance=0.0034,
                                local_name='Smallplace'),
               napi.AddressLine(place_id=1001, osm_object=('N', 3334),
                                category=('place', 'city'),
                                names={'name': 'Bigplace'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=16, distance=0.0,
                                local_name='Bigplace'),
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'country_code'),
                                names={'ref': 'pl'}, extratags={},
                                admin_level=None, fromarea=True, isaddress=False,
                                rank_address=4, distance=0.0)
           ]


def test_lookup_in_tiger(apiobj):
    apiobj.add_tiger(place_id=4924,
                     parent_place_id=12,
                     startnumber=1, endnumber=4, step=1,
                     postcode='34425',
                     geometry='LINESTRING(23 34, 23 35)')
    apiobj.add_placex(place_id=12,
                      category=('highway', 'residential'),
                      osm_type='W', osm_id=6601223,
                      geometry='LINESTRING(23 34, 23 35)')

    result = apiobj.api.details(napi.PlaceID(4924))

    assert result is not None

    assert result.source_table.name == 'TIGER'
    assert result.category == ('place', 'houses')
    assert result.centroid == (pytest.approx(23.0), pytest.approx(34.5))

    assert result.place_id == 4924
    assert result.parent_place_id == 12
    assert result.linked_place_id is None
    assert result.osm_object == ('W', 6601223)
    assert result.admin_level == 15

    assert result.names is None
    assert result.address is None
    assert result.extratags == {'startnumber': '1', 'endnumber': '4', 'step': '1'}

    assert result.housenumber is None
    assert result.postcode == '34425'
    assert result.wikipedia is None

    assert result.rank_search == 30
    assert result.rank_address == 30
    assert result.importance is None

    assert result.country_code == 'us'
    assert result.indexed_date is None

    assert result.address_rows is None
    assert result.linked_rows is None
    assert result.parented_rows is None
    assert result.name_keywords is None
    assert result.address_keywords is None

    assert result.geometry == {'type': 'ST_LineString'}


def test_lookup_tiger_with_address_details(apiobj):
    apiobj.add_tiger(place_id=9000,
                     startnumber=2, endnumber=4, step=1,
                     parent_place_id=332)
    apiobj.add_placex(place_id=332, osm_type='W', osm_id=4,
                     class_='highway', type='residential',  name='Street',
                     country_code='us',
                     rank_search=27, rank_address=26)
    apiobj.add_address_placex(332, fromarea=False, isaddress=False,
                              distance=0.0034,
                              place_id=1000, osm_type='N', osm_id=3333,
                              class_='place', type='suburb', name='Smallplace',
                              country_code='us', admin_level=13,
                              rank_search=24, rank_address=23)
    apiobj.add_address_placex(332, fromarea=True, isaddress=True,
                              place_id=1001, osm_type='N', osm_id=3334,
                              class_='place', type='city', name='Bigplace',
                              country_code='us',
                              rank_search=17, rank_address=16)

    result = apiobj.api.details(napi.PlaceID(9000), address_details=True)

    assert result.address_rows == [
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'house_number'),
                                names={'ref': '2'}, extratags={},
                                admin_level=None, fromarea=True, isaddress=True,
                                rank_address=28, distance=0.0,
                                local_name='2'),
               napi.AddressLine(place_id=332, osm_object=('W', 4),
                                category=('highway', 'residential'),
                                names={'name': 'Street'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=26, distance=0.0,
                                local_name='Street'),
               napi.AddressLine(place_id=1000, osm_object=('N', 3333),
                                category=('place', 'suburb'),
                                names={'name': 'Smallplace'}, extratags={},
                                admin_level=13, fromarea=False, isaddress=True,
                                rank_address=23, distance=0.0034,
                                local_name='Smallplace'),
               napi.AddressLine(place_id=1001, osm_object=('N', 3334),
                                category=('place', 'city'),
                                names={'name': 'Bigplace'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=16, distance=0.0,
                                local_name='Bigplace'),
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'country_code'),
                                names={'ref': 'us'}, extratags={},
                                admin_level=None, fromarea=True, isaddress=False,
                                rank_address=4, distance=0.0)
           ]


def test_lookup_in_postcode(apiobj):
    import_date = dt.datetime(2022, 12, 7, 14, 14, 46, 0)
    apiobj.add_postcode(place_id=554,
                        parent_place_id=152,
                        postcode='34 425',
                        country_code='gb',
                        rank_search=20, rank_address=22,
                        indexed_date=import_date,
                        geometry='POINT(-9.45 5.6)')

    result = apiobj.api.details(napi.PlaceID(554))

    assert result is not None

    assert result.source_table.name == 'POSTCODE'
    assert result.category == ('place', 'postcode')
    assert result.centroid == (pytest.approx(-9.45), pytest.approx(5.6))

    assert result.place_id == 554
    assert result.parent_place_id == 152
    assert result.linked_place_id is None
    assert result.osm_object is None
    assert result.admin_level == 15

    assert result.names == {'ref': '34 425'}
    assert result.address is None
    assert result.extratags is None

    assert result.housenumber is None
    assert result.postcode is None
    assert result.wikipedia is None

    assert result.rank_search == 20
    assert result.rank_address == 22
    assert result.importance is None

    assert result.country_code == 'gb'
    assert result.indexed_date == import_date.replace(tzinfo=dt.timezone.utc)

    assert result.address_rows is None
    assert result.linked_rows is None
    assert result.parented_rows is None
    assert result.name_keywords is None
    assert result.address_keywords is None

    assert result.geometry == {'type': 'ST_Point'}


def test_lookup_postcode_with_address_details(apiobj):
    apiobj.add_postcode(place_id=9000,
                        parent_place_id=332,
                        postcode='34 425',
                        country_code='gb',
                        rank_search=25, rank_address=25)
    apiobj.add_placex(place_id=332, osm_type='N', osm_id=3333,
                      class_='place', type='suburb',  name='Smallplace',
                      country_code='gb', admin_level=13,
                      rank_search=24, rank_address=23)
    apiobj.add_address_placex(332, fromarea=True, isaddress=True,
                              place_id=1001, osm_type='N', osm_id=3334,
                              class_='place', type='city', name='Bigplace',
                              country_code='gb',
                              rank_search=17, rank_address=16)

    result = apiobj.api.details(napi.PlaceID(9000), address_details=True)

    assert result.address_rows == [
               napi.AddressLine(place_id=332, osm_object=('N', 3333),
                                category=('place', 'suburb'),
                                names={'name': 'Smallplace'}, extratags={},
                                admin_level=13, fromarea=True, isaddress=True,
                                rank_address=23, distance=0.0,
                                local_name='Smallplace'),
               napi.AddressLine(place_id=1001, osm_object=('N', 3334),
                                category=('place', 'city'),
                                names={'name': 'Bigplace'}, extratags={},
                                admin_level=15, fromarea=True, isaddress=True,
                                rank_address=16, distance=0.0,
                                local_name='Bigplace'),
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'postcode'),
                                names={'ref': '34 425'}, extratags={},
                                admin_level=None, fromarea=False, isaddress=True,
                                rank_address=5, distance=0.0,
                                local_name='34 425'),
               napi.AddressLine(place_id=None, osm_object=None,
                                category=('place', 'country_code'),
                                names={'ref': 'gb'}, extratags={},
                                admin_level=None, fromarea=True, isaddress=False,
                                rank_address=4, distance=0.0)
           ]

@pytest.mark.parametrize('objid', [napi.PlaceID(1736),
                                   napi.OsmID('W', 55),
                                   napi.OsmID('N', 55, 'amenity')])
def test_lookup_missing_object(apiobj, objid):
    apiobj.add_placex(place_id=1, osm_type='N', osm_id=55,
                      class_='place', type='suburb')

    assert apiobj.api.details(objid) is None


@pytest.mark.parametrize('gtype', (napi.GeometryFormat.KML,
                                    napi.GeometryFormat.SVG,
                                    napi.GeometryFormat.TEXT))
def test_lookup_unsupported_geometry(apiobj, gtype):
    apiobj.add_placex(place_id=332)

    with pytest.raises(ValueError):
        apiobj.api.details(napi.PlaceID(332), geometry_output=gtype)
