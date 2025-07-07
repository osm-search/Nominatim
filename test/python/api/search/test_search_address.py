# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for running the address searcher.
"""
import pytest

import nominatim_api as napi
from nominatim_api.types import SearchDetails
from nominatim_api.search.db_searches import AddressSearch
from nominatim_api.search.db_search_fields import WeightedStrings, WeightedCategories, \
                                                  FieldLookup, FieldRanking, RankedTokens
from nominatim_api.search.db_search_lookups import LookupAll

APIOPTIONS = ['search']


def run_search(apiobj, frontend, global_penalty, lookup, ranking, count=2,
               hnrs=[], pcs=[], ccodes=[], quals=[], has_address=False,
               details=SearchDetails()):
    class MySearchData:
        penalty = global_penalty
        postcodes = WeightedStrings(pcs, [0.0] * len(pcs))
        countries = WeightedStrings(ccodes, [0.0] * len(ccodes))
        housenumbers = WeightedStrings(hnrs, [0.0] * len(hnrs))
        qualifiers = WeightedCategories(quals, [0.0] * len(quals))
        lookups = lookup
        rankings = ranking

    search = AddressSearch(0.0, MySearchData(), count, has_address)

    if frontend is None:
        api = apiobj
    else:
        api = frontend(apiobj, options=APIOPTIONS)

    async def run():
        async with api._async_api.begin() as conn:
            return await search.lookup(conn, details)

    results = api._loop.run_until_complete(run())
    results.sort(key=lambda r: r.accuracy)

    return results


class TestStreetWithHousenumber:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_placex(place_id=1, class_='place', type='house',
                          parent_place_id=1000,
                          housenumber='20 a', country_code='es')
        apiobj.add_placex(place_id=2, class_='place', type='house',
                          parent_place_id=1000,
                          housenumber='21;22', country_code='es')
        apiobj.add_placex(place_id=1000, class_='highway', type='residential',
                          rank_search=26, rank_address=26,
                          country_code='es')
        apiobj.add_search_name(1000, names=[1, 2, 10, 11],
                               search_rank=26, address_rank=26,
                               country_code='es')
        apiobj.add_placex(place_id=91, class_='place', type='house',
                          parent_place_id=2000,
                          housenumber='20', country_code='pt')
        apiobj.add_placex(place_id=92, class_='place', type='house',
                          parent_place_id=2000,
                          housenumber='22', country_code='pt')
        apiobj.add_placex(place_id=93, class_='place', type='house',
                          parent_place_id=2000,
                          housenumber='24', country_code='pt')
        apiobj.add_placex(place_id=2000, class_='highway', type='residential',
                          rank_search=26, rank_address=26,
                          country_code='pt')
        apiobj.add_search_name(2000, names=[1, 2, 20, 21],
                               search_rank=26, address_rank=26,
                               country_code='pt')

    @pytest.mark.parametrize('hnr,res', [('20', [91, 1]), ('20 a', [1]),
                                         ('21', [2]), ('22', [2, 92]),
                                         ('24', [93]), ('25', [])])
    def test_lookup_by_single_housenumber(self, apiobj, frontend, hnr, res):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=[hnr])

        assert [r.place_id for r in results] == res + [1000, 2000]

    @pytest.mark.parametrize('cc,res', [('es', [2, 1000]), ('pt', [92, 2000])])
    def test_lookup_with_country_restriction(self, apiobj, frontend, cc, res):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             ccodes=[cc])

        assert [r.place_id for r in results] == res

    def test_lookup_exclude_housenumber_placeid(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             details=SearchDetails(excluded=[92]))

        assert [r.place_id for r in results] == [2, 1000, 2000]

    def test_lookup_exclude_street_placeid(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             details=SearchDetails(excluded=[1000]))

        assert [r.place_id for r in results] == [2, 92, 2000]

    def test_lookup_only_house_qualifier(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             quals=[('place', 'house')])

        assert [r.place_id for r in results] == [2, 92]

    def test_lookup_only_street_qualifier(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             quals=[('highway', 'residential')])

        assert [r.place_id for r in results] == [1000, 2000]

    @pytest.mark.parametrize('rank,found', [(26, True), (27, False), (30, False)])
    def test_lookup_min_rank(self, apiobj, frontend, rank, found):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             details=SearchDetails(min_rank=rank))

        assert [r.place_id for r in results] == ([2, 92, 1000, 2000] if found else [2, 92])

    @pytest.mark.parametrize('geom', [napi.GeometryFormat.GEOJSON,
                                      napi.GeometryFormat.KML,
                                      napi.GeometryFormat.SVG,
                                      napi.GeometryFormat.TEXT])
    def test_return_geometries(self, apiobj, frontend, geom):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)

        results = run_search(apiobj, frontend, 0.1, [lookup], [], hnrs=['20', '21', '22'],
                             details=SearchDetails(geometry_output=geom))

        assert results
        assert all(geom.name.lower() in r.geometry for r in results)


def test_very_large_housenumber(apiobj, frontend):
    apiobj.add_placex(place_id=93, class_='place', type='house',
                      parent_place_id=2000,
                      housenumber='2467463524544', country_code='pt')
    apiobj.add_placex(place_id=2000, class_='highway', type='residential',
                      rank_search=26, rank_address=26,
                      country_code='pt')
    apiobj.add_search_name(2000, names=[1, 2],
                           search_rank=26, address_rank=26,
                           country_code='pt')

    lookup = FieldLookup('name_vector', [1, 2], LookupAll)

    results = run_search(apiobj, frontend, 0.1, [lookup], [], hnrs=['2467463524544'],
                         details=SearchDetails())

    assert results
    assert [r.place_id for r in results] == [93, 2000]


class TestInterpolations:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_placex(place_id=990, class_='highway', type='service',
                          rank_search=27, rank_address=27,
                          centroid=(10.0, 10.0),
                          geometry='LINESTRING(9.995 10, 10.005 10)')
        apiobj.add_search_name(990, names=[111],
                               search_rank=27, address_rank=27)
        apiobj.add_placex(place_id=991, class_='place', type='house',
                          parent_place_id=990,
                          rank_search=30, rank_address=30,
                          housenumber='23',
                          centroid=(10.0, 10.00002))
        apiobj.add_osmline(place_id=992,
                           parent_place_id=990,
                           startnumber=21, endnumber=29, step=2,
                           centroid=(10.0, 10.00001),
                           geometry='LINESTRING(9.995 10.00001, 10.005 10.00001)')

    @pytest.mark.parametrize('hnr,res', [('21', [992]), ('22', []), ('23', [991])])
    def test_lookup_housenumber(self, apiobj, frontend, hnr, res):
        lookup = FieldLookup('name_vector', [111], LookupAll)

        results = run_search(apiobj, frontend, 0.1, [lookup], [], hnrs=[hnr])

        assert [r.place_id for r in results] == res + [990]

    @pytest.mark.parametrize('geom', [napi.GeometryFormat.GEOJSON,
                                      napi.GeometryFormat.KML,
                                      napi.GeometryFormat.SVG,
                                      napi.GeometryFormat.TEXT])
    def test_osmline_with_geometries(self, apiobj, frontend, geom):
        lookup = FieldLookup('name_vector', [111], LookupAll)

        results = run_search(apiobj, frontend, 0.1, [lookup], [], hnrs=['21'],
                             details=SearchDetails(geometry_output=geom))

        assert results[0].place_id == 992
        assert geom.name.lower() in results[0].geometry


class TestTiger:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_placex(place_id=990, class_='highway', type='service',
                          rank_search=27, rank_address=27,
                          country_code='us',
                          centroid=(10.0, 10.0),
                          geometry='LINESTRING(9.995 10, 10.005 10)')
        apiobj.add_search_name(990, names=[111], country_code='us',
                               search_rank=27, address_rank=27)
        apiobj.add_placex(place_id=991, class_='place', type='house',
                          parent_place_id=990,
                          rank_search=30, rank_address=30,
                          housenumber='23',
                          country_code='us',
                          centroid=(10.0, 10.00002))
        apiobj.add_tiger(place_id=992,
                         parent_place_id=990,
                         startnumber=21, endnumber=29, step=2,
                         centroid=(10.0, 10.00001),
                         geometry='LINESTRING(9.995 10.00001, 10.005 10.00001)')

    @pytest.mark.parametrize('hnr,res', [('21', [992]), ('22', []), ('23', [991])])
    def test_lookup_housenumber(self, apiobj, frontend, hnr, res):
        lookup = FieldLookup('name_vector', [111], LookupAll)

        results = run_search(apiobj, frontend, 0.1, [lookup], [], hnrs=[hnr])

        assert [r.place_id for r in results] == res + [990]

    @pytest.mark.parametrize('geom', [napi.GeometryFormat.GEOJSON,
                                      napi.GeometryFormat.KML,
                                      napi.GeometryFormat.SVG,
                                      napi.GeometryFormat.TEXT])
    def test_tiger_with_geometries(self, apiobj, frontend, geom):
        lookup = FieldLookup('name_vector', [111], LookupAll)

        results = run_search(apiobj, frontend, 0.1, [lookup], [], hnrs=['21'],
                             details=SearchDetails(geometry_output=geom))

        assert results[0].place_id == 992
        assert geom.name.lower() in results[0].geometry
