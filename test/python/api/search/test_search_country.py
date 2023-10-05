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


@pytest.mark.parametrize('coord,numres', [((0.5, 1), 1), ((10, 10), 0)])
def test_find_near(apiobj, coord, numres):
    apiobj.add_country('ro', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
    apiobj.add_country_name('ro', {'name': 'România'})

    results = run_search(apiobj, 0.0, ['ro'],
                         details=SearchDetails(near=napi.Point(*coord),
                                               near_radius=0.1))

    assert len(results) == numres


class TestCountryParameters:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_placex(place_id=55, class_='boundary', type='administrative',
                          rank_search=4, rank_address=4,
                          name={'name': 'Lolaland'},
                          country_code='yw',
                          centroid=(10, 10),
                          geometry='POLYGON((9.5 9.5, 9.5 10.5, 10.5 10.5, 10.5 9.5, 9.5 9.5))')
        apiobj.add_country('ro', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
        apiobj.add_country_name('ro', {'name': 'România'})


    @pytest.mark.parametrize('geom', [napi.GeometryFormat.GEOJSON,
                                      napi.GeometryFormat.KML,
                                      napi.GeometryFormat.SVG,
                                      napi.GeometryFormat.TEXT])
    @pytest.mark.parametrize('cc', ['yw', 'ro'])
    def test_return_geometries(self, apiobj, geom, cc):
        results = run_search(apiobj, 0.5, [cc],
                             details=SearchDetails(geometry_output=geom))

        assert len(results) == 1
        assert geom.name.lower() in results[0].geometry


    @pytest.mark.parametrize('pid,rids', [(76, [55]), (55, [])])
    def test_exclude_place_id(self, apiobj, pid, rids):
        results = run_search(apiobj, 0.5, ['yw', 'ro'],
                             details=SearchDetails(excluded=[pid]))

        assert [r.place_id for r in results] == rids


    @pytest.mark.parametrize('viewbox,rids', [((9, 9, 11, 11), [55]),
                                              ((-10, -10, -3, -3), [])])
    def test_bounded_viewbox_in_placex(self, apiobj, viewbox, rids):
        results = run_search(apiobj, 0.5, ['yw'],
                             details=SearchDetails.from_kwargs({'viewbox': viewbox,
                                                                'bounded_viewbox': True}))

        assert [r.place_id for r in results] == rids


    @pytest.mark.parametrize('viewbox,numres', [((0, 0, 1, 1), 1),
                                              ((-10, -10, -3, -3), 0)])
    def test_bounded_viewbox_in_fallback(self, apiobj, viewbox, numres):
        results = run_search(apiobj, 0.5, ['ro'],
                             details=SearchDetails.from_kwargs({'viewbox': viewbox,
                                                                'bounded_viewbox': True}))

        assert len(results) == numres
