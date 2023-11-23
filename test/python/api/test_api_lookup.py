# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for lookup API call.
"""
import json

import pytest

import nominatim.api as napi

def test_lookup_empty_list(apiobj, frontend):
    api = frontend(apiobj, options={'details'})
    assert api.lookup([]) == []


def test_lookup_non_existing(apiobj, frontend):
    api = frontend(apiobj, options={'details'})
    assert api.lookup((napi.PlaceID(332), napi.OsmID('W', 4),
                       napi.OsmID('W', 4, 'highway'))) == []


@pytest.mark.parametrize('idobj', (napi.PlaceID(332), napi.OsmID('W', 4),
                                   napi.OsmID('W', 4, 'highway')))
def test_lookup_single_placex(apiobj, frontend, idobj):
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
                     geometry='LINESTRING(23 34, 23.1 34, 23.1 34.1, 23 34)')

    api = frontend(apiobj, options={'details'})
    result = api.lookup([idobj])

    assert len(result) == 1

    result = result[0]

    assert result.source_table.name == 'PLACEX'
    assert result.category == ('highway', 'residential')
    assert result.centroid == (pytest.approx(23.0), pytest.approx(34.0))

    assert result.place_id == 332
    assert result.osm_object == ('W', 4)

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

    assert result.address_rows is None
    assert result.linked_rows is None
    assert result.parented_rows is None
    assert result.name_keywords is None
    assert result.address_keywords is None

    assert result.geometry == {}


def test_lookup_multiple_places(apiobj, frontend):
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
                     geometry='LINESTRING(23 34, 23.1 34, 23.1 34.1, 23 34)')
    apiobj.add_osmline(place_id=4924, osm_id=9928,
                       parent_place_id=12,
                       startnumber=1, endnumber=4, step=1,
                       country_code='gb', postcode='34425',
                       address={'city': 'Big'},
                       geometry='LINESTRING(23 34, 23 35)')


    api = frontend(apiobj, options={'details'})
    result = api.lookup((napi.OsmID('W', 1),
                         napi.OsmID('W', 4),
                         napi.OsmID('W', 9928)))

    assert len(result) == 2

    assert set(r.place_id for r in result) == {332, 4924}


@pytest.mark.parametrize('gtype', list(napi.GeometryFormat))
def test_simple_place_with_geometry(apiobj, frontend, gtype):
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
                     geometry='POLYGON((23 34, 23.1 34, 23.1 34.1, 23 34))')

    api = frontend(apiobj, options={'details'})
    result = api.lookup([napi.OsmID('W', 4)], geometry_output=gtype)

    assert len(result) == 1
    assert result[0].place_id == 332

    if gtype == napi.GeometryFormat.NONE:
        assert list(result[0].geometry.keys()) == []
    else:
        assert list(result[0].geometry.keys()) == [gtype.name.lower()]


def test_simple_place_with_geometry_simplified(apiobj, frontend):
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
                     geometry='POLYGON((23 34, 22.999 34, 23.1 34, 23.1 34.1, 23 34))')

    api = frontend(apiobj, options={'details'})
    result = api.lookup([napi.OsmID('W', 4)],
                        geometry_output=napi.GeometryFormat.GEOJSON,
                        geometry_simplification=0.1)

    assert len(result) == 1
    assert result[0].place_id == 332

    geom = json.loads(result[0].geometry['geojson'])

    assert geom['type']  == 'Polygon'
    assert geom['coordinates'] == [[[23, 34], [23.1, 34], [23.1, 34.1], [23, 34]]]
