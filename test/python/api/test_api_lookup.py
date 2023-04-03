# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for lookup API call.
"""
import pytest

import nominatim.api as napi

def test_lookup_empty_list(apiobj):
    assert apiobj.api.lookup([]) == []


def test_lookup_non_existing(apiobj):
    assert apiobj.api.lookup((napi.PlaceID(332), napi.OsmID('W', 4),
                              napi.OsmID('W', 4, 'highway'))) == []


@pytest.mark.parametrize('idobj', (napi.PlaceID(332), napi.OsmID('W', 4),
                                   napi.OsmID('W', 4, 'highway')))
def test_lookup_single_placex(apiobj, idobj):
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

    result = apiobj.api.lookup([idobj])

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


def test_lookup_multiple_places(apiobj):
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


    result = apiobj.api.lookup((napi.OsmID('W', 1),
                                napi.OsmID('W', 4),
                                napi.OsmID('W', 9928)), napi.LookupDetails())

    assert len(result) == 2

    assert set(r.place_id for r in result) == {332, 4924}
