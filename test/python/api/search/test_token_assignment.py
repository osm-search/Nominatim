# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for creation of token assignments from tokenized queries.
"""
import pytest

from nominatim.api.search.query import QueryStruct, Phrase, PhraseType, BreakType, TokenType, TokenRange, Token
from nominatim.api.search.token_assignment import yield_token_assignments, TokenAssignment, PENALTY_TOKENCHANGE

class MyToken(Token):
    def get_category(self):
        return 'this', 'that'


def make_query(*args):
    q = None
    dummy = MyToken(3.0, 45, 1, 'foo', True)

    for btype, ptype, tlist in args:
        if q is None:
            q = QueryStruct([Phrase(ptype, '')])
        else:
            q.add_node(btype, ptype)

        start = len(q.nodes) - 1
        for end, ttype in tlist:
            q.add_token(TokenRange(start, end), ttype, dummy)

    q.add_node(BreakType.END, PhraseType.NONE)

    return q


def check_assignments(actual, *expected):
    todo = list(expected)
    for assignment in actual:
        assert assignment in todo, f"Unexpected assignment: {assignment}"
        todo.remove(assignment)

    assert not todo, f"Missing assignments: {expected}"


def test_query_with_missing_tokens():
    q = QueryStruct([Phrase(PhraseType.NONE, '')])
    q.add_node(BreakType.END, PhraseType.NONE)

    assert list(yield_token_assignments(q)) == []


def test_one_word_query():
    q = make_query((BreakType.START, PhraseType.NONE,
                    [(1, TokenType.PARTIAL),
                     (1, TokenType.WORD),
                     (1, TokenType.HOUSENUMBER)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(name=TokenRange(0, 1))]


def test_single_postcode():
    q = make_query((BreakType.START, PhraseType.NONE,
                    [(1, TokenType.POSTCODE)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(postcode=TokenRange(0, 1))]


def test_single_country_name():
    q = make_query((BreakType.START, PhraseType.NONE,
                    [(1, TokenType.COUNTRY)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(country=TokenRange(0, 1))]


def test_single_word_poi_search():
    q = make_query((BreakType.START, PhraseType.NONE,
                    [(1, TokenType.CATEGORY),
                     (1, TokenType.QUALIFIER)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(category=TokenRange(0, 1))]


@pytest.mark.parametrize('btype', [BreakType.WORD, BreakType.PART, BreakType.TOKEN])
def test_multiple_simple_words(btype):
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (btype, PhraseType.NONE, [(2, TokenType.PARTIAL)]),
                   (btype, PhraseType.NONE, [(3, TokenType.PARTIAL)]))

    penalty = PENALTY_TOKENCHANGE[btype]

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(0, 3)),
                      TokenAssignment(penalty=penalty, name=TokenRange(0, 2),
                                      address=[TokenRange(2, 3)]),
                      TokenAssignment(penalty=penalty, name=TokenRange(0, 1),
                                      address=[TokenRange(1, 3)]),
                      TokenAssignment(penalty=penalty, name=TokenRange(1, 3),
                                      address=[TokenRange(0, 1)]),
                      TokenAssignment(penalty=penalty, name=TokenRange(2, 3),
                                      address=[TokenRange(0, 2)])
                     )


def test_multiple_words_respect_phrase_break():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(2, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(0, 1),
                                      address=[TokenRange(1, 2)]),
                      TokenAssignment(name=TokenRange(1, 2),
                                      address=[TokenRange(0, 1)]))


def test_housenumber_and_street():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.HOUSENUMBER)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(2, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(1, 2),
                                      housenumber=TokenRange(0, 1)),
                      TokenAssignment(address=[TokenRange(1, 2)],
                                      housenumber=TokenRange(0, 1)))


def test_housenumber_and_street_backwards():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(2, TokenType.HOUSENUMBER)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(0, 1),
                                      housenumber=TokenRange(1, 2)),
                      TokenAssignment(address=[TokenRange(0, 1)],
                                      housenumber=TokenRange(1, 2)))


def test_housenumber_and_postcode():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.HOUSENUMBER)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(4, TokenType.POSTCODE)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=pytest.approx(0.3),
                                      name=TokenRange(0, 1),
                                      housenumber=TokenRange(1, 2),
                                      address=[TokenRange(2, 3)],
                                      postcode=TokenRange(3, 4)),
                      TokenAssignment(penalty=pytest.approx(0.3),
                                      housenumber=TokenRange(1, 2),
                                      address=[TokenRange(0, 1), TokenRange(2, 3)],
                                      postcode=TokenRange(3, 4)))

def test_postcode_and_housenumber():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.POSTCODE)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(4, TokenType.HOUSENUMBER)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=pytest.approx(0.3),
                                      name=TokenRange(2, 3),
                                      housenumber=TokenRange(3, 4),
                                      address=[TokenRange(0, 1)],
                                      postcode=TokenRange(1, 2)),
                      TokenAssignment(penalty=pytest.approx(0.3),
                                      housenumber=TokenRange(3, 4),
                                      address=[TokenRange(0, 1), TokenRange(2, 3)],
                                      postcode=TokenRange(1, 2)))


def test_country_housenumber_postcode():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.COUNTRY)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.HOUSENUMBER)]),
                   (BreakType.WORD, PhraseType.NONE, [(4, TokenType.POSTCODE)]))

    check_assignments(yield_token_assignments(q))


@pytest.mark.parametrize('ttype', [TokenType.POSTCODE, TokenType.COUNTRY,
                                   TokenType.CATEGORY, TokenType.QUALIFIER])
def test_housenumber_with_only_special_terms(ttype):
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.HOUSENUMBER)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, ttype)]))

    check_assignments(yield_token_assignments(q))


@pytest.mark.parametrize('ttype', [TokenType.POSTCODE, TokenType.HOUSENUMBER, TokenType.COUNTRY])
def test_multiple_special_tokens(ttype):
    q = make_query((BreakType.START, PhraseType.NONE, [(1, ttype)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(2, TokenType.PARTIAL)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(3, ttype)]))

    check_assignments(yield_token_assignments(q))


def test_housenumber_many_phrases():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(2, TokenType.PARTIAL)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(3, TokenType.PARTIAL)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(4, TokenType.HOUSENUMBER)]),
                   (BreakType.WORD, PhraseType.NONE, [(5, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1,
                                      name=TokenRange(4, 5),
                                      housenumber=TokenRange(3, 4),\
                                      address=[TokenRange(0, 1), TokenRange(1, 2),
                                               TokenRange(2, 3)]),
                      TokenAssignment(penalty=0.1,
                                      housenumber=TokenRange(3, 4),\
                                      address=[TokenRange(0, 1), TokenRange(1, 2),
                                               TokenRange(2, 3), TokenRange(4, 5)]))


def test_country_at_beginning():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.COUNTRY)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(1, 2),
                                      country=TokenRange(0, 1)))


def test_country_at_end():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.COUNTRY)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(0, 1),
                                      country=TokenRange(1, 2)))


def test_country_in_middle():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.COUNTRY)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q))


def test_postcode_with_designation():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.POSTCODE)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(2, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(1, 2),
                                      postcode=TokenRange(0, 1)),
                      TokenAssignment(postcode=TokenRange(0, 1),
                                      address=[TokenRange(1, 2)]))


def test_postcode_with_designation_backwards():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.PHRASE, PhraseType.NONE, [(2, TokenType.POSTCODE)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(0, 1),
                                      postcode=TokenRange(1, 2)),
                      TokenAssignment(postcode=TokenRange(1, 2),
                                      address=[TokenRange(0, 1)]))


def test_category_at_beginning():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.CATEGORY)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(1, 2),
                                      category=TokenRange(0, 1)))


def test_category_at_end():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.CATEGORY)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(0, 1),
                                      category=TokenRange(1, 2)))


def test_category_in_middle():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.CATEGORY)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q))


def test_qualifier_at_beginning():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.QUALIFIER)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.PARTIAL)]))


    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(1, 3),
                                      qualifier=TokenRange(0, 1)),
                      TokenAssignment(penalty=0.2, name=TokenRange(1, 2),
                                      qualifier=TokenRange(0, 1),
                                      address=[TokenRange(2, 3)]))


def test_qualifier_after_name():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.QUALIFIER)]),
                   (BreakType.WORD, PhraseType.NONE, [(4, TokenType.PARTIAL)]),
                   (BreakType.WORD, PhraseType.NONE, [(5, TokenType.PARTIAL)]))


    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.2, name=TokenRange(0, 2),
                                      qualifier=TokenRange(2, 3),
                                      address=[TokenRange(3, 5)]),
                      TokenAssignment(penalty=0.2, name=TokenRange(3, 5),
                                      qualifier=TokenRange(2, 3),
                                      address=[TokenRange(0, 2)]))


def test_qualifier_before_housenumber():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.QUALIFIER)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.HOUSENUMBER)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q))


def test_qualifier_after_housenumber():
    q = make_query((BreakType.START, PhraseType.NONE, [(1, TokenType.HOUSENUMBER)]),
                   (BreakType.WORD, PhraseType.NONE, [(2, TokenType.QUALIFIER)]),
                   (BreakType.WORD, PhraseType.NONE, [(3, TokenType.PARTIAL)]))

    check_assignments(yield_token_assignments(q))
