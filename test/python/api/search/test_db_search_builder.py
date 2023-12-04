# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for creating abstract searches from token assignments.
"""
import pytest

from nominatim.api.search.query import Token, TokenRange, BreakType, PhraseType, TokenType, QueryStruct, Phrase
from nominatim.api.search.db_search_builder import SearchBuilder
from nominatim.api.search.token_assignment import TokenAssignment
from nominatim.api.types import SearchDetails
import nominatim.api.search.db_searches as dbs

class MyToken(Token):
    def get_category(self):
        return 'this', 'that'


def make_query(*args):
    q = QueryStruct([Phrase(PhraseType.NONE, '')])

    for _ in range(max(inner[0] for tlist in args for inner in tlist)):
        q.add_node(BreakType.WORD, PhraseType.NONE)
    q.add_node(BreakType.END, PhraseType.NONE)

    for start, tlist in enumerate(args):
        for end, ttype, tinfo in tlist:
            for tid, word in tinfo:
                q.add_token(TokenRange(start, end), ttype,
                            MyToken(0.5 if ttype == TokenType.PARTIAL else 0.0, tid, 1, word, True))


    return q


def test_country_search():
    q = make_query([(1, TokenType.COUNTRY, [(2, 'de'), (3, 'en')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(country=TokenRange(0, 1))))

    assert len(searches) == 1

    search = searches[0]

    assert isinstance(search, dbs.CountrySearch)
    assert set(search.countries.values) == {'de', 'en'}


def test_country_search_with_country_restriction():
    q = make_query([(1, TokenType.COUNTRY, [(2, 'de'), (3, 'en')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'countries': 'en,fr'}))

    searches = list(builder.build(TokenAssignment(country=TokenRange(0, 1))))

    assert len(searches) == 1

    search = searches[0]

    assert isinstance(search, dbs.CountrySearch)
    assert set(search.countries.values) == {'en'}


def test_country_search_with_conflicting_country_restriction():
    q = make_query([(1, TokenType.COUNTRY, [(2, 'de'), (3, 'en')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'countries': 'fr'}))

    searches = list(builder.build(TokenAssignment(country=TokenRange(0, 1))))

    assert len(searches) == 0


def test_postcode_search_simple():
    q = make_query([(1, TokenType.POSTCODE, [(34, '2367')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(postcode=TokenRange(0, 1))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PostcodeSearch)
    assert search.postcodes.values == ['2367']
    assert not search.countries.values
    assert not search.lookups
    assert not search.rankings


def test_postcode_with_country():
    q = make_query([(1, TokenType.POSTCODE, [(34, '2367')])],
                   [(2, TokenType.COUNTRY, [(1, 'xx')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(postcode=TokenRange(0, 1),
                                                  country=TokenRange(1, 2))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PostcodeSearch)
    assert search.postcodes.values == ['2367']
    assert search.countries.values == ['xx']
    assert not search.lookups
    assert not search.rankings


def test_postcode_with_address():
    q = make_query([(1, TokenType.POSTCODE, [(34, '2367')])],
                   [(2, TokenType.PARTIAL, [(100, 'word')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(postcode=TokenRange(0, 1),
                                                  address=[TokenRange(1, 2)])))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PostcodeSearch)
    assert search.postcodes.values == ['2367']
    assert not search.countries
    assert search.lookups
    assert not search.rankings


def test_postcode_with_address_with_full_word():
    q = make_query([(1, TokenType.POSTCODE, [(34, '2367')])],
                   [(2, TokenType.PARTIAL, [(100, 'word')]),
                    (2, TokenType.WORD, [(1, 'full')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(postcode=TokenRange(0, 1),
                                                  address=[TokenRange(1, 2)])))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PostcodeSearch)
    assert search.postcodes.values == ['2367']
    assert not search.countries
    assert search.lookups
    assert len(search.rankings) == 1


@pytest.mark.parametrize('kwargs', [{'viewbox': '0,0,1,1', 'bounded_viewbox': True},
                                    {'near': '10,10'}])
def test_near_item_only(kwargs):
    q = make_query([(1, TokenType.NEAR_ITEM, [(2, 'foo')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs(kwargs))

    searches = list(builder.build(TokenAssignment(near_item=TokenRange(0, 1))))

    assert len(searches) == 1

    search = searches[0]

    assert isinstance(search, dbs.PoiSearch)
    assert search.qualifiers.values == [('this', 'that')]


@pytest.mark.parametrize('kwargs', [{'viewbox': '0,0,1,1'},
                                    {}])
def test_near_item_skipped(kwargs):
    q = make_query([(1, TokenType.NEAR_ITEM, [(2, 'foo')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs(kwargs))

    searches = list(builder.build(TokenAssignment(near_item=TokenRange(0, 1))))

    assert len(searches) == 0


def test_name_only_search():
    q = make_query([(1, TokenType.PARTIAL, [(1, 'a')]),
                    (1, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(name=TokenRange(0, 1))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert not search.postcodes.values
    assert not search.countries.values
    assert not search.housenumbers.values
    assert not search.qualifiers.values
    assert len(search.lookups) == 1
    assert len(search.rankings) == 1


def test_name_with_qualifier():
    q = make_query([(1, TokenType.PARTIAL, [(1, 'a')]),
                    (1, TokenType.WORD, [(100, 'a')])],
                   [(2, TokenType.QUALIFIER, [(55, 'hotel')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(name=TokenRange(0, 1),
                                                  qualifier=TokenRange(1, 2))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert not search.postcodes.values
    assert not search.countries.values
    assert not search.housenumbers.values
    assert search.qualifiers.values == [('this', 'that')]
    assert len(search.lookups) == 1
    assert len(search.rankings) == 1


def test_name_with_housenumber_search():
    q = make_query([(1, TokenType.PARTIAL, [(1, 'a')]),
                    (1, TokenType.WORD, [(100, 'a')])],
                   [(2, TokenType.HOUSENUMBER, [(66, '66')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(name=TokenRange(0, 1),
                                                  housenumber=TokenRange(1, 2))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert not search.postcodes.values
    assert not search.countries.values
    assert search.housenumbers.values == ['66']
    assert len(search.lookups) == 1
    assert len(search.rankings) == 1


def test_name_and_address():
    q = make_query([(1, TokenType.PARTIAL, [(1, 'a')]),
                    (1, TokenType.WORD, [(100, 'a')])],
                   [(2, TokenType.PARTIAL, [(2, 'b')]),
                    (2, TokenType.WORD, [(101, 'b')])],
                   [(3, TokenType.PARTIAL, [(3, 'c')]),
                    (3, TokenType.WORD, [(102, 'c')])]
                  )
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(name=TokenRange(0, 1),
                                                  address=[TokenRange(1, 2),
                                                           TokenRange(2, 3)])))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert not search.postcodes.values
    assert not search.countries.values
    assert not search.housenumbers.values
    assert len(search.lookups) == 2
    assert len(search.rankings) == 3


def test_name_and_complex_address():
    q = make_query([(1, TokenType.PARTIAL, [(1, 'a')]),
                    (1, TokenType.WORD, [(100, 'a')])],
                   [(2, TokenType.PARTIAL, [(2, 'b')]),
                    (3, TokenType.WORD, [(101, 'bc')])],
                   [(3, TokenType.PARTIAL, [(3, 'c')])],
                   [(4, TokenType.PARTIAL, [(4, 'd')]),
                    (4, TokenType.WORD, [(103, 'd')])]
                  )
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(name=TokenRange(0, 1),
                                                  address=[TokenRange(1, 2),
                                                           TokenRange(2, 4)])))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert not search.postcodes.values
    assert not search.countries.values
    assert not search.housenumbers.values
    assert len(search.lookups) == 2
    assert len(search.rankings) == 2


def test_name_only_near_search():
    q = make_query([(1, TokenType.NEAR_ITEM, [(88, 'g')])],
                   [(2, TokenType.PARTIAL, [(1, 'a')]),
                    (2, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails())

    searches = list(builder.build(TokenAssignment(name=TokenRange(1, 2),
                                                  near_item=TokenRange(0, 1))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.NearSearch)
    assert isinstance(search.search, dbs.PlaceSearch)


def test_name_only_search_with_category():
    q = make_query([(1, TokenType.PARTIAL, [(1, 'a')]),
                    (1, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'categories': [('foo', 'bar')]}))

    searches = list(builder.build(TokenAssignment(name=TokenRange(0, 1))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert search.qualifiers.values == [('foo', 'bar')]


def test_name_with_near_item_search_with_category_mismatch():
    q = make_query([(1, TokenType.NEAR_ITEM, [(88, 'g')])],
                   [(2, TokenType.PARTIAL, [(1, 'a')]),
                    (2, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'categories': [('foo', 'bar')]}))

    searches = list(builder.build(TokenAssignment(name=TokenRange(1, 2),
                                                  near_item=TokenRange(0, 1))))

    assert len(searches) == 0


def test_name_with_near_item_search_with_category_match():
    q = make_query([(1, TokenType.NEAR_ITEM, [(88, 'g')])],
                   [(2, TokenType.PARTIAL, [(1, 'a')]),
                    (2, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'categories': [('foo', 'bar'),
                                                                         ('this', 'that')]}))

    searches = list(builder.build(TokenAssignment(name=TokenRange(1, 2),
                                                  near_item=TokenRange(0, 1))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.NearSearch)
    assert isinstance(search.search, dbs.PlaceSearch)


def test_name_with_qualifier_search_with_category_mismatch():
    q = make_query([(1, TokenType.QUALIFIER, [(88, 'g')])],
                   [(2, TokenType.PARTIAL, [(1, 'a')]),
                    (2, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'categories': [('foo', 'bar')]}))

    searches = list(builder.build(TokenAssignment(name=TokenRange(1, 2),
                                                  qualifier=TokenRange(0, 1))))

    assert len(searches) == 0


def test_name_with_qualifier_search_with_category_match():
    q = make_query([(1, TokenType.QUALIFIER, [(88, 'g')])],
                   [(2, TokenType.PARTIAL, [(1, 'a')]),
                    (2, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'categories': [('foo', 'bar'),
                                                                         ('this', 'that')]}))

    searches = list(builder.build(TokenAssignment(name=TokenRange(1, 2),
                                                  qualifier=TokenRange(0, 1))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert search.qualifiers.values == [('this', 'that')]


def test_name_only_search_with_countries():
    q = make_query([(1, TokenType.PARTIAL, [(1, 'a')]),
                    (1, TokenType.WORD, [(100, 'a')])])
    builder = SearchBuilder(q, SearchDetails.from_kwargs({'countries': 'de,en'}))

    searches = list(builder.build(TokenAssignment(name=TokenRange(0, 1))))

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert not search.postcodes.values
    assert set(search.countries.values) == {'de', 'en'}
    assert not search.housenumbers.values


def make_counted_searches(name_part, name_full, address_part, address_full,
                          num_address_parts=1):
    q = QueryStruct([Phrase(PhraseType.NONE, '')])
    for i in range(1 + num_address_parts):
        q.add_node(BreakType.WORD, PhraseType.NONE)
    q.add_node(BreakType.END, PhraseType.NONE)

    q.add_token(TokenRange(0, 1), TokenType.PARTIAL,
                MyToken(0.5, 1, name_part, 'name_part', True))
    q.add_token(TokenRange(0, 1), TokenType.WORD,
                MyToken(0, 101, name_full, 'name_full', True))
    for i in range(num_address_parts):
        q.add_token(TokenRange(i + 1, i + 2), TokenType.PARTIAL,
                    MyToken(0.5, 2, address_part, 'address_part', True))
        q.add_token(TokenRange(i + 1, i + 2), TokenType.WORD,
                    MyToken(0, 102, address_full, 'address_full', True))

    builder = SearchBuilder(q, SearchDetails())

    return list(builder.build(TokenAssignment(name=TokenRange(0, 1),
                                              address=[TokenRange(1, 1 + num_address_parts)])))


def test_infrequent_partials_in_name():
    searches = make_counted_searches(1, 1, 1, 1)

    assert len(searches) == 1
    search = searches[0]

    assert isinstance(search, dbs.PlaceSearch)
    assert len(search.lookups) == 2
    assert len(search.rankings) == 2

    assert set((l.column, l.lookup_type) for l in search.lookups) == \
            {('name_vector', 'lookup_all'), ('nameaddress_vector', 'restrict')}


def test_frequent_partials_in_name_and_address():
    searches = make_counted_searches(9999, 1, 9999, 1)

    assert len(searches) == 2

    assert all(isinstance(s, dbs.PlaceSearch) for s in searches)
    searches.sort(key=lambda s: s.penalty)

    assert set((l.column, l.lookup_type) for l in searches[0].lookups) == \
            {('name_vector', 'lookup_any'), ('nameaddress_vector', 'restrict')}
    assert set((l.column, l.lookup_type) for l in searches[1].lookups) == \
            {('nameaddress_vector', 'lookup_all'), ('name_vector', 'lookup_all')}


def test_too_frequent_partials_in_name_and_address():
    searches = make_counted_searches(20000, 1, 10000, 1)

    assert len(searches) == 1

    assert all(isinstance(s, dbs.PlaceSearch) for s in searches)
    searches.sort(key=lambda s: s.penalty)

    assert set((l.column, l.lookup_type) for l in searches[0].lookups) == \
            {('name_vector', 'lookup_any'), ('nameaddress_vector', 'restrict')}
