# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for running the near searcher.
"""
import pytest

import nominatim_api as napi
from nominatim_api.types import SearchDetails
from nominatim_api.search.db_searches import NearSearch, PlaceSearch
from nominatim_api.search.db_search_fields import WeightedStrings, WeightedCategories, \
                                                  FieldLookup
from nominatim_api.search.db_search_lookups import LookupAll


def run_search(apiobj, frontend, global_penalty, cat, cat_penalty=None, ccodes=[],
               details=SearchDetails()):

    class PlaceSearchData:
        penalty = 0.0
        postcodes = WeightedStrings([], [])
        countries = WeightedStrings(ccodes, [0.0] * len(ccodes))
        housenumbers = WeightedStrings([], [])
        qualifiers = WeightedStrings([], [])
        lookups = [FieldLookup('name_vector', [56], LookupAll)]
        rankings = []

    if ccodes is not None:
        details.countries = ccodes

    place_search = PlaceSearch(0.0, PlaceSearchData(), 2)

    if cat_penalty is None:
        cat_penalty = [0.0] * len(cat)

    near_search = NearSearch(0.1, WeightedCategories(cat, cat_penalty), place_search)

    api = frontend(apiobj, options=['search'])

    async def run():
        async with api._async_api.begin() as conn:
            return await near_search.lookup(conn, details)

    results = api._loop.run_until_complete(run())
    results.sort(key=lambda r: r.accuracy)

    return results


def test_no_results_inner_query(apiobj, frontend):
    assert not run_search(apiobj, frontend, 0.4, [('this', 'that')])


def test_no_appropriate_results_inner_query(apiobj, frontend):
    apiobj.add_placex(place_id=100, country_code='us',
                      centroid=(5.6, 4.3),
                      geometry='POLYGON((0.0 0.0, 10.0 0.0, 10.0 2.0, 0.0 2.0, 0.0 0.0))')
    apiobj.add_search_name(100, names=[56], country_code='us',
                           centroid=(5.6, 4.3))
    apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                      centroid=(5.6001, 4.2994))

    assert not run_search(apiobj, frontend, 0.4, [('amenity', 'bank')])


class TestNearSearch:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_placex(place_id=100, country_code='us',
                          centroid=(5.6, 4.3))
        apiobj.add_search_name(100, names=[56], country_code='us',
                               centroid=(5.6, 4.3))
        apiobj.add_placex(place_id=101, country_code='mx',
                          centroid=(-10.3, 56.9))
        apiobj.add_search_name(101, names=[56], country_code='mx',
                               centroid=(-10.3, 56.9))

    def test_near_in_placex(self, apiobj, frontend):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          centroid=(5.6001, 4.2994))
        apiobj.add_placex(place_id=23, class_='amenity', type='bench',
                          centroid=(5.6001, 4.2994))

        results = run_search(apiobj, frontend, 0.1, [('amenity', 'bank')])

        assert [r.place_id for r in results] == [22]

    def test_multiple_types_near_in_placex(self, apiobj, frontend):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          importance=0.002,
                          centroid=(5.6001, 4.2994))
        apiobj.add_placex(place_id=23, class_='amenity', type='bench',
                          importance=0.001,
                          centroid=(5.6001, 4.2994))

        results = run_search(apiobj, frontend, 0.1, [('amenity', 'bank'),
                                                     ('amenity', 'bench')])

        assert [r.place_id for r in results] == [22, 23]

    def test_near_in_classtype(self, apiobj, frontend):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          centroid=(5.6, 4.34))
        apiobj.add_placex(place_id=23, class_='amenity', type='bench',
                          centroid=(5.6, 4.34))
        apiobj.add_class_type_table('amenity', 'bank')
        apiobj.add_class_type_table('amenity', 'bench')

        results = run_search(apiobj, frontend, 0.1, [('amenity', 'bank')])

        assert [r.place_id for r in results] == [22]

    @pytest.mark.parametrize('cc,rid', [('us', 22), ('mx', 23)])
    def test_restrict_by_country(self, apiobj, frontend, cc, rid):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          centroid=(5.6001, 4.2994),
                          country_code='us')
        apiobj.add_placex(place_id=122, class_='amenity', type='bank',
                          centroid=(5.6001, 4.2994),
                          country_code='mx')
        apiobj.add_placex(place_id=23, class_='amenity', type='bank',
                          centroid=(-10.3001, 56.9),
                          country_code='mx')
        apiobj.add_placex(place_id=123, class_='amenity', type='bank',
                          centroid=(-10.3001, 56.9),
                          country_code='us')

        results = run_search(apiobj, frontend, 0.1, [('amenity', 'bank')], ccodes=[cc, 'fr'])

        assert [r.place_id for r in results] == [rid]

    @pytest.mark.parametrize('excluded,rid', [(22, 122), (122, 22)])
    def test_exclude_place_by_id(self, apiobj, frontend, excluded, rid):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          centroid=(5.6001, 4.2994),
                          country_code='us')
        apiobj.add_placex(place_id=122, class_='amenity', type='bank',
                          centroid=(5.6001, 4.2994),
                          country_code='us')

        results = run_search(apiobj, frontend, 0.1, [('amenity', 'bank')],
                             details=SearchDetails(excluded=[excluded]))

        assert [r.place_id for r in results] == [rid]

    @pytest.mark.parametrize('layer,rids', [(napi.DataLayer.POI, [22]),
                                            (napi.DataLayer.MANMADE, [])])
    def test_with_layer(self, apiobj, frontend, layer, rids):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          centroid=(5.6001, 4.2994),
                          country_code='us')

        results = run_search(apiobj, frontend, 0.1, [('amenity', 'bank')],
                             details=SearchDetails(layers=layer))

        assert [r.place_id for r in results] == rids
