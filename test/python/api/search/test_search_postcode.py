# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for running the postcode searcher.
"""
import pytest

import nominatim_api as napi
from nominatim_api.types import SearchDetails
from nominatim_api.search.db_searches import PostcodeSearch
from nominatim_api.search.db_search_fields import WeightedStrings, FieldLookup, \
                                                  FieldRanking, RankedTokens


def run_search(apiobj, frontend, global_penalty, pcs, pc_penalties=None,
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

    api = frontend(apiobj, options=['search'])

    async def run():
        async with api._async_api.begin() as conn:
            return await search.lookup(conn, details)

    return api._loop.run_until_complete(run())


def test_postcode_only_search(apiobj, frontend):
    apiobj.add_postcode(place_id=100, country_code='ch', postcode='12345')
    apiobj.add_postcode(place_id=101, country_code='pl', postcode='12 345')

    results = run_search(apiobj, frontend, 0.3, ['12345', '12 345'], [0.0, 0.1])

    assert len(results) == 2
    assert [r.place_id for r in results] == [100, 101]


def test_postcode_with_country(apiobj, frontend):
    apiobj.add_postcode(place_id=100, country_code='ch', postcode='12345')
    apiobj.add_postcode(place_id=101, country_code='pl', postcode='12 345')

    results = run_search(apiobj, frontend, 0.3, ['12345', '12 345'], [0.0, 0.1],
                         ccodes=['de', 'pl'])

    assert len(results) == 1
    assert results[0].place_id == 101


def test_postcode_area(apiobj, frontend):
    apiobj.add_postcode(place_id=100, country_code='ch', postcode='12345')
    apiobj.add_placex(place_id=200, country_code='ch', postcode='12345',
                      osm_type='R', osm_id=34, class_='boundary', type='postal_code',
                      geometry='POLYGON((0 0, 1 0, 1 1, 0 1, 0 0))')

    results = run_search(apiobj, frontend, 0.3, ['12345'], [0.0])

    assert len(results) == 1
    assert results[0].place_id == 200
    assert results[0].bbox.area == 1


class TestPostcodeSearchWithAddress:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_postcode(place_id=100, country_code='ch',
                            parent_place_id=1000, postcode='12345',
                            geometry='POINT(17 5)')
        apiobj.add_postcode(place_id=101, country_code='pl',
                            parent_place_id=2000, postcode='12345',
                            geometry='POINT(-45 7)')
        apiobj.add_placex(place_id=1000, class_='place', type='village',
                          rank_search=22, rank_address=22,
                          country_code='ch')
        apiobj.add_search_name(1000, names=[1, 2, 10, 11],
                               search_rank=22, address_rank=22,
                               country_code='ch')
        apiobj.add_placex(place_id=2000, class_='place', type='village',
                          rank_search=22, rank_address=22,
                          country_code='pl')
        apiobj.add_search_name(2000, names=[1, 2, 20, 21],
                               search_rank=22, address_rank=22,
                               country_code='pl')

    def test_lookup_both(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1, 2], 'restrict')
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, ['12345'], lookup=[lookup], ranking=[ranking])

        assert [r.place_id for r in results] == [100, 101]

    def test_restrict_by_name(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [10], 'restrict')

        results = run_search(apiobj, frontend, 0.1, ['12345'], lookup=[lookup])

        assert [r.place_id for r in results] == [100]

    @pytest.mark.parametrize('coord,place_id', [((16.5, 5), 100),
                                                ((-45.1, 7.004), 101)])
    def test_lookup_near(self, apiobj, frontend, coord, place_id):
        lookup = FieldLookup('name_vector', [1, 2], 'restrict')
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, ['12345'],
                             lookup=[lookup], ranking=[ranking],
                             details=SearchDetails(near=napi.Point(*coord),
                                                   near_radius=0.6))

        assert [r.place_id for r in results] == [place_id]

    @pytest.mark.parametrize('geom', [napi.GeometryFormat.GEOJSON,
                                      napi.GeometryFormat.KML,
                                      napi.GeometryFormat.SVG,
                                      napi.GeometryFormat.TEXT])
    def test_return_geometries(self, apiobj, frontend, geom):
        results = run_search(apiobj, frontend, 0.1, ['12345'],
                             details=SearchDetails(geometry_output=geom))

        assert results
        assert all(geom.name.lower() in r.geometry for r in results)

    @pytest.mark.parametrize('viewbox, rids', [('-46,6,-44,8', [101, 100]),
                                               ('16,4,18,6', [100, 101])])
    def test_prefer_viewbox(self, apiobj, frontend, viewbox, rids):
        results = run_search(apiobj, frontend, 0.1, ['12345'],
                             details=SearchDetails.from_kwargs({'viewbox': viewbox}))

        assert [r.place_id for r in results] == rids

    @pytest.mark.parametrize('viewbox, rid', [('-46,6,-44,8', 101),
                                              ('16,4,18,6', 100)])
    def test_restrict_to_viewbox(self, apiobj, frontend, viewbox, rid):
        results = run_search(apiobj, frontend, 0.1, ['12345'],
                             details=SearchDetails.from_kwargs({'viewbox': viewbox,
                                                                'bounded_viewbox': True}))

        assert [r.place_id for r in results] == [rid]

    @pytest.mark.parametrize('coord,rids', [((17.05, 5), [100, 101]),
                                            ((-45, 7.1), [101, 100])])
    def test_prefer_near(self, apiobj, frontend, coord, rids):
        results = run_search(apiobj, frontend, 0.1, ['12345'],
                             details=SearchDetails(near=napi.Point(*coord)))

        assert [r.place_id for r in results] == rids

    @pytest.mark.parametrize('pid,rid', [(100, 101), (101, 100)])
    def test_exclude(self, apiobj, frontend, pid, rid):
        results = run_search(apiobj, frontend, 0.1, ['12345'],
                             details=SearchDetails(excluded=[pid]))

        assert [r.place_id for r in results] == [rid]
