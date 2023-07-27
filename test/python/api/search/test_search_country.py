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
Tests for running the country searcher.
"""
import pytest

import nominatim.api as napi
from nominatim.api.types import SearchDetails
from nominatim.api.search.db_searches import CountrySearch
from nominatim.api.search.db_search_fields import WeightedStrings


def run_search(apiobj, global_penalty, ccodes,
               country_penalties=None, details=SearchDetails()):
    if country_penalties is None:
        country_penalties = [0.0] * len(ccodes)

    class MySearchData:
        penalty = global_penalty
        countries = WeightedStrings(ccodes, country_penalties)

    search = CountrySearch(MySearchData())

    async def run():
        async with apiobj.api._async_api.begin() as conn:
            return await search.lookup(conn, details)

    return apiobj.async_to_sync(run())


def test_find_from_placex(apiobj):
    apiobj.add_placex(place_id=55, class_='boundary', type='administrative',
                      rank_search=4, rank_address=4,
                      name={'name': 'Lolaland'},
                      country_code='yw',
                      centroid=(10, 10),
                      geometry='POLYGON((9.5 9.5, 9.5 10.5, 10.5 10.5, 10.5 9.5, 9.5 9.5))')

    results = run_search(apiobj, 0.5, ['de', 'yw'], [0.0, 0.3])

    assert len(results) == 1
    assert results[0].place_id == 55
    assert results[0].accuracy == 0.8

def test_find_from_fallback_countries(apiobj):
    apiobj.add_country('ro', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
    apiobj.add_country_name('ro', {'name': 'România'})

    results = run_search(apiobj, 0.0, ['ro'])

    assert len(results) == 1
    assert results[0].names == {'name': 'România'}


def test_find_none(apiobj):
    assert len(run_search(apiobj, 0.0, ['xx'])) == 0
