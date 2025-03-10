# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for creation of token assignments from tokenized queries.
"""
import pytest

from nominatim_api.search.query import QueryStruct, Phrase, TokenRange, Token
import nominatim_api.search.query as qmod
from nominatim_api.search.token_assignment import (yield_token_assignments,
                                                   TokenAssignment,
                                                   PENALTY_TOKENCHANGE)


class MyToken(Token):
    def get_category(self):
        return 'this', 'that'


def make_query(*args):
    q = QueryStruct([Phrase(args[0][1], '')])
    dummy = MyToken(penalty=3.0, token=45, count=1, addr_count=1,
                    lookup_word='foo')

    for btype, ptype, _ in args[1:]:
        q.add_node(btype, ptype)
    q.add_node(qmod.BREAK_END, qmod.PHRASE_ANY)

    for start, t in enumerate(args):
        for end, ttype in t[2]:
            q.add_token(TokenRange(start, end), ttype, dummy)

    return q


def check_assignments(actual, *expected):
    todo = list(expected)
    for assignment in actual:
        assert assignment in todo, f"Unexpected assignment: {assignment}"
        todo.remove(assignment)

    assert not todo, f"Missing assignments: {expected}"


def test_query_with_missing_tokens():
    q = QueryStruct([Phrase(qmod.PHRASE_ANY, '')])
    q.add_node(qmod.BREAK_END, qmod.PHRASE_ANY)

    assert list(yield_token_assignments(q)) == []


def test_one_word_query():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY,
                    [(1, qmod.TOKEN_PARTIAL),
                     (1, qmod.TOKEN_WORD),
                     (1, qmod.TOKEN_HOUSENUMBER)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(name=TokenRange(0, 1))]


def test_single_postcode():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY,
                    [(1, qmod.TOKEN_POSTCODE)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(postcode=TokenRange(0, 1))]


def test_single_country_name():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY,
                    [(1, qmod.TOKEN_COUNTRY)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(country=TokenRange(0, 1))]


def test_single_word_poi_search():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY,
                    [(1, qmod.TOKEN_NEAR_ITEM),
                     (1, qmod.TOKEN_QUALIFIER)]))

    res = list(yield_token_assignments(q))
    assert res == [TokenAssignment(near_item=TokenRange(0, 1))]


@pytest.mark.parametrize('btype', [qmod.BREAK_WORD, qmod.BREAK_PART, qmod.BREAK_TOKEN])
def test_multiple_simple_words(btype):
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (btype, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]),
                   (btype, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]))

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
                                      address=[TokenRange(0, 2)]))


def test_multiple_words_respect_phrase_break():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(0, 1),
                                      address=[TokenRange(1, 2)]),
                      TokenAssignment(name=TokenRange(1, 2),
                                      address=[TokenRange(0, 1)]))


def test_housenumber_and_street():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_HOUSENUMBER)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(1, 2),
                                      housenumber=TokenRange(0, 1)),
                      TokenAssignment(address=[TokenRange(1, 2)],
                                      housenumber=TokenRange(0, 1)))


def test_housenumber_and_street_backwards():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_HOUSENUMBER)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(0, 1),
                                      housenumber=TokenRange(1, 2)),
                      TokenAssignment(address=[TokenRange(0, 1)],
                                      housenumber=TokenRange(1, 2)))


def test_housenumber_and_postcode():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_HOUSENUMBER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(4, qmod.TOKEN_POSTCODE)]))

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
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_POSTCODE)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(4, qmod.TOKEN_HOUSENUMBER)]))

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
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_COUNTRY)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_HOUSENUMBER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(4, qmod.TOKEN_POSTCODE)]))

    check_assignments(yield_token_assignments(q))


@pytest.mark.parametrize('ttype', [qmod.TOKEN_POSTCODE, qmod.TOKEN_COUNTRY,
                                   qmod.TOKEN_NEAR_ITEM, qmod.TOKEN_QUALIFIER])
def test_housenumber_with_only_special_terms(ttype):
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_HOUSENUMBER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, ttype)]))

    check_assignments(yield_token_assignments(q))


@pytest.mark.parametrize('ttype', [qmod.TOKEN_POSTCODE, qmod.TOKEN_HOUSENUMBER, qmod.TOKEN_COUNTRY])
def test_multiple_special_tokens(ttype):
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, ttype)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(3, ttype)]))

    check_assignments(yield_token_assignments(q))


def test_housenumber_many_phrases():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(4, qmod.TOKEN_HOUSENUMBER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(5, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1,
                                      name=TokenRange(4, 5),
                                      housenumber=TokenRange(3, 4),
                                      address=[TokenRange(0, 1), TokenRange(1, 2),
                                               TokenRange(2, 3)]),
                      TokenAssignment(penalty=0.1,
                                      housenumber=TokenRange(3, 4),
                                      address=[TokenRange(0, 1), TokenRange(1, 2),
                                               TokenRange(2, 3), TokenRange(4, 5)]))


def test_country_at_beginning():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_COUNTRY)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(1, 2),
                                      country=TokenRange(0, 1)))


def test_country_at_end():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_COUNTRY)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(0, 1),
                                      country=TokenRange(1, 2)))


def test_country_in_middle():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_COUNTRY)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q))


def test_postcode_with_designation():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_POSTCODE)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(1, 2),
                                      postcode=TokenRange(0, 1)),
                      TokenAssignment(postcode=TokenRange(0, 1),
                                      address=[TokenRange(1, 2)]))


def test_postcode_with_designation_backwards():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_POSTCODE)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(name=TokenRange(0, 1),
                                      postcode=TokenRange(1, 2)),
                      TokenAssignment(penalty=0.1, postcode=TokenRange(1, 2),
                                      address=[TokenRange(0, 1)]))


def test_near_item_at_beginning():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_NEAR_ITEM)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(1, 2),
                                      near_item=TokenRange(0, 1)))


def test_near_item_at_end():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_NEAR_ITEM)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(0, 1),
                                      near_item=TokenRange(1, 2)))


def test_near_item_in_middle():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_NEAR_ITEM)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q))


def test_qualifier_at_beginning():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_QUALIFIER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.1, name=TokenRange(1, 3),
                                      qualifier=TokenRange(0, 1)),
                      TokenAssignment(penalty=0.2, name=TokenRange(1, 2),
                                      qualifier=TokenRange(0, 1),
                                      address=[TokenRange(2, 3)]))


def test_qualifier_after_name():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_QUALIFIER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(4, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(5, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q),
                      TokenAssignment(penalty=0.2, name=TokenRange(0, 2),
                                      qualifier=TokenRange(2, 3),
                                      address=[TokenRange(3, 5)]),
                      TokenAssignment(penalty=0.2, name=TokenRange(3, 5),
                                      qualifier=TokenRange(2, 3),
                                      address=[TokenRange(0, 2)]))


def test_qualifier_before_housenumber():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_QUALIFIER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_HOUSENUMBER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q))


def test_qualifier_after_housenumber():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_HOUSENUMBER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(2, qmod.TOKEN_QUALIFIER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q))


def test_qualifier_in_middle_of_phrase():
    q = make_query((qmod.BREAK_START, qmod.PHRASE_ANY, [(1, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(2, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(3, qmod.TOKEN_QUALIFIER)]),
                   (qmod.BREAK_WORD, qmod.PHRASE_ANY, [(4, qmod.TOKEN_PARTIAL)]),
                   (qmod.BREAK_PHRASE, qmod.PHRASE_ANY, [(5, qmod.TOKEN_PARTIAL)]))

    check_assignments(yield_token_assignments(q))
