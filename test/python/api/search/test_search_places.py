# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for running the generic place searcher.
"""
import json

import pytest

import nominatim.api as napi
from nominatim.api.types import SearchDetails
from nominatim.api.search.db_searches import PlaceSearch
from nominatim.api.search.db_search_fields import WeightedStrings, WeightedCategories,\
                                                  FieldLookup, FieldRanking, RankedTokens
from nominatim.api.search.db_search_lookups import LookupAll, LookupAny, Restrict

APIOPTIONS = ['search']

def run_search(apiobj, frontend, global_penalty, lookup, ranking, count=2,
               hnrs=[], pcs=[], ccodes=[], quals=[],
               details=SearchDetails()):
    class MySearchData:
        penalty = global_penalty
        postcodes = WeightedStrings(pcs, [0.0] * len(pcs))
        countries = WeightedStrings(ccodes, [0.0] * len(ccodes))
        housenumbers = WeightedStrings(hnrs, [0.0] * len(hnrs))
        qualifiers = WeightedCategories(quals, [0.0] * len(quals))
        lookups = lookup
        rankings = ranking

    search = PlaceSearch(0.0, MySearchData(), count)

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


class TestNameOnlySearches:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_placex(place_id=100, country_code='us',
                          centroid=(5.6, 4.3))
        apiobj.add_search_name(100, names=[1,2,10,11], country_code='us',
                               centroid=(5.6, 4.3))
        apiobj.add_placex(place_id=101, country_code='mx',
                          centroid=(-10.3, 56.9))
        apiobj.add_search_name(101, names=[1,2,20,21], country_code='mx',
                               centroid=(-10.3, 56.9))


    @pytest.mark.parametrize('lookup_type', [LookupAll, Restrict])
    @pytest.mark.parametrize('rank,res', [([10], [100, 101]),
                                          ([20], [101, 100])])
    def test_lookup_all_match(self, apiobj, frontend, lookup_type, rank, res):
        lookup = FieldLookup('name_vector', [1,2], lookup_type)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, rank)])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking])

        assert [r.place_id for r in results] == res


    @pytest.mark.parametrize('lookup_type', [LookupAll, Restrict])
    def test_lookup_all_partial_match(self, apiobj, frontend, lookup_type):
        lookup = FieldLookup('name_vector', [1,20], lookup_type)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, [21])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking])

        assert len(results) == 1
        assert results[0].place_id == 101

    @pytest.mark.parametrize('rank,res', [([10], [100, 101]),
                                          ([20], [101, 100])])
    def test_lookup_any_match(self, apiobj, frontend, rank, res):
        lookup = FieldLookup('name_vector', [11,21], LookupAny)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, rank)])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking])

        assert [r.place_id for r in results] == res


    def test_lookup_any_partial_match(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [20], LookupAll)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, [21])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking])

        assert len(results) == 1
        assert results[0].place_id == 101


    @pytest.mark.parametrize('cc,res', [('us', 100), ('mx', 101)])
    def test_lookup_restrict_country(self, apiobj, frontend, cc, res):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], ccodes=[cc])

        assert [r.place_id for r in results] == [res]


    def test_lookup_restrict_placeid(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking],
                             details=SearchDetails(excluded=[101]))

        assert [r.place_id for r in results] == [100]


    @pytest.mark.parametrize('geom', [napi.GeometryFormat.GEOJSON,
                                      napi.GeometryFormat.KML,
                                      napi.GeometryFormat.SVG,
                                      napi.GeometryFormat.TEXT])
    def test_return_geometries(self, apiobj, frontend, geom):
        lookup = FieldLookup('name_vector', [20], LookupAll)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, [21])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking],
                             details=SearchDetails(geometry_output=geom))

        assert geom.name.lower() in results[0].geometry


    @pytest.mark.parametrize('factor,npoints', [(0.0, 3), (1.0, 2)])
    def test_return_simplified_geometry(self, apiobj, frontend, factor, npoints):
        apiobj.add_placex(place_id=333, country_code='us',
                          centroid=(9.0, 9.0),
                          geometry='LINESTRING(8.9 9.0, 9.0 9.0, 9.1 9.0)')
        apiobj.add_search_name(333, names=[55], country_code='us',
                               centroid=(5.6, 4.3))

        lookup = FieldLookup('name_vector', [55], LookupAll)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, [21])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking],
                             details=SearchDetails(geometry_output=napi.GeometryFormat.GEOJSON,
                                                   geometry_simplification=factor))

        assert len(results) == 1
        result = results[0]
        geom = json.loads(result.geometry['geojson'])

        assert result.place_id == 333
        assert len(geom['coordinates']) == npoints


    @pytest.mark.parametrize('viewbox', ['5.0,4.0,6.0,5.0', '5.7,4.0,6.0,5.0'])
    @pytest.mark.parametrize('wcount,rids', [(2, [100, 101]), (20000, [100])])
    def test_prefer_viewbox(self, apiobj, frontend, viewbox, wcount, rids):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.2, [RankedTokens(0.0, [21])])

        api = frontend(apiobj, options=APIOPTIONS)
        results = run_search(api, None, 0.1, [lookup], [ranking])
        assert [r.place_id for r in results] == [101, 100]

        results = run_search(api, None, 0.1, [lookup], [ranking], count=wcount,
                             details=SearchDetails.from_kwargs({'viewbox': viewbox}))
        assert [r.place_id for r in results] == rids


    @pytest.mark.parametrize('viewbox', ['5.0,4.0,6.0,5.0', '5.55,4.27,5.62,4.31'])
    def test_force_viewbox(self, apiobj, frontend, viewbox):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)

        details=SearchDetails.from_kwargs({'viewbox': viewbox,
                                           'bounded_viewbox': True})

        results = run_search(apiobj, frontend, 0.1, [lookup], [], details=details)
        assert [r.place_id for r in results] == [100]


    def test_prefer_near(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)
        ranking = FieldRanking('name_vector', 0.4, [RankedTokens(0.0, [21])])

        api = frontend(apiobj, options=APIOPTIONS)
        results = run_search(api, None, 0.1, [lookup], [ranking])
        assert [r.place_id for r in results] == [101, 100]

        results = run_search(api, None, 0.1, [lookup], [ranking],
                             details=SearchDetails.from_kwargs({'near': '5.6,4.3'}))
        results.sort(key=lambda r: -r.importance)
        assert [r.place_id for r in results] == [100, 101]


    @pytest.mark.parametrize('radius', [0.09, 0.11])
    def test_force_near(self, apiobj, frontend, radius):
        lookup = FieldLookup('name_vector', [1, 2], LookupAll)

        details=SearchDetails.from_kwargs({'near': '5.6,4.3',
                                           'near_radius': radius})

        results = run_search(apiobj, frontend, 0.1, [lookup], [], details=details)

        assert [r.place_id for r in results] == [100]


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
        apiobj.add_search_name(1000, names=[1,2,10,11],
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
        apiobj.add_search_name(2000, names=[1,2,20,21],
                               search_rank=26, address_rank=26,
                               country_code='pt')


    @pytest.mark.parametrize('hnr,res', [('20', [91, 1]), ('20 a', [1]),
                                         ('21', [2]), ('22', [2, 92]),
                                         ('24', [93]), ('25', [])])
    def test_lookup_by_single_housenumber(self, apiobj, frontend, hnr, res):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=[hnr])

        assert [r.place_id for r in results] == res + [1000, 2000]


    @pytest.mark.parametrize('cc,res', [('es', [2, 1000]), ('pt', [92, 2000])])
    def test_lookup_with_country_restriction(self, apiobj, frontend, cc, res):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             ccodes=[cc])

        assert [r.place_id for r in results] == res


    def test_lookup_exclude_housenumber_placeid(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             details=SearchDetails(excluded=[92]))

        assert [r.place_id for r in results] == [2, 1000, 2000]


    def test_lookup_exclude_street_placeid(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             details=SearchDetails(excluded=[1000]))

        assert [r.place_id for r in results] == [2, 92, 2000]


    def test_lookup_only_house_qualifier(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             quals=[('place', 'house')])

        assert [r.place_id for r in results] == [2, 92]


    def test_lookup_only_street_qualifier(self, apiobj, frontend):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
        ranking = FieldRanking('name_vector', 0.3, [RankedTokens(0.0, [10])])

        results = run_search(apiobj, frontend, 0.1, [lookup], [ranking], hnrs=['22'],
                             quals=[('highway', 'residential')])

        assert [r.place_id for r in results] == [1000, 2000]


    @pytest.mark.parametrize('rank,found', [(26, True), (27, False), (30, False)])
    def test_lookup_min_rank(self, apiobj, frontend, rank, found):
        lookup = FieldLookup('name_vector', [1,2], LookupAll)
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
    apiobj.add_search_name(2000, names=[1,2],
                           search_rank=26, address_rank=26,
                           country_code='pt')

    lookup = FieldLookup('name_vector', [1, 2], LookupAll)

    results = run_search(apiobj, frontend, 0.1, [lookup], [], hnrs=['2467463524544'],
                         details=SearchDetails())

    assert results
    assert [r.place_id for r in results] == [93, 2000]


@pytest.mark.parametrize('wcount,rids', [(2, [990, 991]), (30000, [990])])
def test_name_and_postcode(apiobj, frontend, wcount, rids):
    apiobj.add_placex(place_id=990, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      postcode='11225',
                      centroid=(10.0, 10.0),
                      geometry='LINESTRING(9.995 10, 10.005 10)')
    apiobj.add_search_name(990, names=[111], centroid=(10.0, 10.0),
                           search_rank=27, address_rank=27)
    apiobj.add_placex(place_id=991, class_='highway', type='service',
                      rank_search=27, rank_address=27,
                      postcode='11221',
                      centroid=(10.3, 10.3),
                      geometry='LINESTRING(9.995 10.3, 10.005 10.3)')
    apiobj.add_search_name(991, names=[111], centroid=(10.3, 10.3),
                           search_rank=27, address_rank=27)
    apiobj.add_postcode(place_id=100, country_code='ch', postcode='11225',
                        geometry='POINT(10 10)')

    lookup = FieldLookup('name_vector', [111], LookupAll)

    results = run_search(apiobj, frontend, 0.1, [lookup], [], pcs=['11225'], count=wcount,
                         details=SearchDetails())

    assert results
    assert [r.place_id for r in results] == rids


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


class TestLayersRank30:

    @pytest.fixture(autouse=True)
    def fill_database(self, apiobj):
        apiobj.add_placex(place_id=223, class_='place', type='house',
                          housenumber='1',
                          rank_address=30,
                          rank_search=30)
        apiobj.add_search_name(223, names=[34],
                               importance=0.0009,
                               address_rank=30, search_rank=30)
        apiobj.add_placex(place_id=224, class_='amenity', type='toilet',
                          rank_address=30,
                          rank_search=30)
        apiobj.add_search_name(224, names=[34],
                               importance=0.0008,
                               address_rank=30, search_rank=30)
        apiobj.add_placex(place_id=225, class_='man_made', type='tower',
                          rank_address=0,
                          rank_search=30)
        apiobj.add_search_name(225, names=[34],
                               importance=0.0007,
                               address_rank=0, search_rank=30)
        apiobj.add_placex(place_id=226, class_='railway', type='station',
                          rank_address=0,
                          rank_search=30)
        apiobj.add_search_name(226, names=[34],
                               importance=0.0006,
                               address_rank=0, search_rank=30)
        apiobj.add_placex(place_id=227, class_='natural', type='cave',
                          rank_address=0,
                          rank_search=30)
        apiobj.add_search_name(227, names=[34],
                               importance=0.0005,
                               address_rank=0, search_rank=30)


    @pytest.mark.parametrize('layer,res', [(napi.DataLayer.ADDRESS, [223]),
                                           (napi.DataLayer.POI, [224]),
                                           (napi.DataLayer.ADDRESS | napi.DataLayer.POI, [223, 224]),
                                           (napi.DataLayer.MANMADE, [225]),
                                           (napi.DataLayer.RAILWAY, [226]),
                                           (napi.DataLayer.NATURAL, [227]),
                                           (napi.DataLayer.MANMADE | napi.DataLayer.NATURAL, [225, 227]),
                                           (napi.DataLayer.MANMADE | napi.DataLayer.RAILWAY, [225, 226])])
    def test_layers_rank30(self, apiobj, frontend, layer, res):
        lookup = FieldLookup('name_vector', [34], LookupAny)

        results = run_search(apiobj, frontend, 0.1, [lookup], [],
                             details=SearchDetails(layers=layer))

        assert [r.place_id for r in results] == res
