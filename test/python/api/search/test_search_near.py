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
Tests for running the near searcher.
"""
import pytest

import nominatim.api as napi
from nominatim.api.types import SearchDetails
from nominatim.api.search.db_searches import NearSearch, PlaceSearch
from nominatim.api.search.db_search_fields import WeightedStrings, WeightedCategories,\
                                                  FieldLookup, FieldRanking, RankedTokens


def run_search(apiobj, global_penalty, cat, cat_penalty=None,
               details=SearchDetails()):

    class PlaceSearchData:
        penalty = 0.0
        postcodes = WeightedStrings([], [])
        countries = WeightedStrings([], [])
        housenumbers = WeightedStrings([], [])
        qualifiers = WeightedStrings([], [])
        lookups = [FieldLookup('name_vector', [56], 'lookup_all')]
        rankings = []

    place_search = PlaceSearch(0.0, PlaceSearchData(), 2)

    if cat_penalty is None:
        cat_penalty = [0.0] * len(cat)

    near_search = NearSearch(0.1, WeightedCategories(cat, cat_penalty), place_search)

    async def run():
        async with apiobj.api._async_api.begin() as conn:
            return await near_search.lookup(conn, details)

    results = apiobj.async_to_sync(run())
    results.sort(key=lambda r: r.accuracy)

    return results


def test_no_results_inner_query(apiobj):
    assert not run_search(apiobj, 0.4, [('this', 'that')])


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


    def test_near_in_placex(self, apiobj):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          centroid=(5.6001, 4.2994))
        apiobj.add_placex(place_id=23, class_='amenity', type='bench',
                          centroid=(5.6001, 4.2994))

        results = run_search(apiobj, 0.1, [('amenity', 'bank')])

        assert [r.place_id for r in results] == [22]


    def test_multiple_types_near_in_placex(self, apiobj):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          importance=0.002,
                          centroid=(5.6001, 4.2994))
        apiobj.add_placex(place_id=23, class_='amenity', type='bench',
                          importance=0.001,
                          centroid=(5.6001, 4.2994))

        results = run_search(apiobj, 0.1, [('amenity', 'bank'),
                                           ('amenity', 'bench')])

        assert [r.place_id for r in results] == [22, 23]


    def test_near_in_classtype(self, apiobj):
        apiobj.add_placex(place_id=22, class_='amenity', type='bank',
                          centroid=(5.6, 4.34))
        apiobj.add_placex(place_id=23, class_='amenity', type='bench',
                          centroid=(5.6, 4.34))
        apiobj.add_class_type_table('amenity', 'bank')
        apiobj.add_class_type_table('amenity', 'bench')

        results = run_search(apiobj, 0.1, [('amenity', 'bank')])

        assert [r.place_id for r in results] == [22]

