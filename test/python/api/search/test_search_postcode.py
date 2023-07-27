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
Tests for running the postcode searcher.
"""
import pytest

import nominatim.api as napi
from nominatim.api.types import SearchDetails
from nominatim.api.search.db_searches import PostcodeSearch
from nominatim.api.search.db_search_fields import WeightedStrings, FieldLookup, \
                                                  FieldRanking, RankedTokens

def run_search(apiobj, global_penalty, pcs, pc_penalties=None,
               ccodes=[], lookup=[], ranking=[], details=SearchDetails()):
    if pc_penalties is None:
        pc_penalties = [0.0] * len(pcs)

    class MySearchData:
        penalty = global_penalty
        postcodes = WeightedStrings(pcs, pc_penalties)
        countries = WeightedStrings(ccodes, [0.0] * len(ccodes))
        lookups = lookup
        rankings = ranking

    search = PostcodeSearch(0.0, MySearchData())

    async def run():
        async with apiobj.api._async_api.begin() as conn:
            return await search.lookup(conn, details)

    return apiobj.async_to_sync(run())


def test_postcode_only_search(apiobj):
    apiobj.add_postcode(place_id=100, country_code='ch', postcode='12345')
    apiobj.add_postcode(place_id=101, country_code='pl', postcode='12 345')

    results = run_search(apiobj, 0.3, ['12345', '12 345'], [0.0, 0.1])

    assert len(results) == 2
    assert [r.place_id for r in results] == [100, 101]


def test_postcode_with_country(apiobj):
    apiobj.add_postcode(place_id=100, country_code='ch', postcode='12345')
    apiobj.add_postcode(place_id=101, country_code='pl', postcode='12 345')

    results = run_search(apiobj, 0.3, ['12345', '12 345'], [0.0, 0.1],
                         ccodes=['de', 'pl'])

    assert len(results) == 1
    assert results[0].place_id == 101


class TestPostcodeSearchWithAddress:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_postcode(place_id=100, country_code='ch',
                            parent_place_id=1000, postcode='12345')
        apiobj.add_postcode(place_id=101, country_code='pl',
                            parent_place_id=2000, postcode='12345')
        apiobj.add_placex(place_id=1000, class_='place', type='village',
                          rank_search=22, rank_address=22,
                          country_code='ch')
        apiobj.add_search_name(1000, names=[1,2,10,11],
                               search_rank=22, address_rank=22,
                               country_code='ch')
        apiobj.add_placex(place_id=2000, class_='place', type='village',
                          rank_search=22, rank_address=22,
                          country_code='pl')
        apiobj.add_search_name(2000, names=[1,2,20,21],
                               search_rank=22, address_rank=22,
                               country_code='pl')


    def test_lookup_both(self, apiobj):
        lookup = FieldLookup('name_vector', [1,2], 'restrict')
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, 0.1, ['12345'], lookup=[lookup], ranking=[ranking])

        assert [r.place_id for r in results] == [100, 101]


    def test_restrict_by_name(self, apiobj):
        lookup = FieldLookup('name_vector', [10], 'restrict')

        results = run_search(apiobj, 0.1, ['12345'], lookup=[lookup])

        assert [r.place_id for r in results] == [100]

