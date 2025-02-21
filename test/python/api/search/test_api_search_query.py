# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for tokenized query data structures.
"""
import pytest

from nominatim_api.search import query

class MyToken(query.Token):

    def get_category(self):
        return 'this', 'that'


def mktoken(tid: int):
    return MyToken(penalty=3.0, token=tid, count=1, addr_count=1,
                   lookup_word='foo')


@pytest.mark.parametrize('ptype,ttype', [('NONE', 'W'),
                                         ('AMENITY', 'Q'),
                                         ('STREET', 'w'),
                                         ('CITY', 'W'),
                                         ('COUNTRY', 'C'),
                                         ('POSTCODE', 'P')])
def test_phrase_compatible(ptype, ttype):
    assert query.PhraseType[ptype].compatible_with(ttype, False)


@pytest.mark.parametrize('ptype', ['COUNTRY', 'POSTCODE'])
def test_phrase_incompatible(ptype):
    assert not query.PhraseType[ptype].compatible_with(query.TOKEN_PARTIAL, True)


def test_query_node_empty():
    qn = query.QueryNode(query.BREAK_PHRASE, query.PhraseType.NONE)

    assert not qn.has_tokens(3, query.TOKEN_PARTIAL)
    assert qn.get_tokens(3, query.TOKEN_WORD) is None


def test_query_node_with_content():
    qn = query.QueryNode(query.BREAK_PHRASE, query.PhraseType.NONE)
    qn.starting.append(query.TokenList(2, query.TOKEN_PARTIAL, [mktoken(100), mktoken(101)]))
    qn.starting.append(query.TokenList(2, query.TOKEN_WORD, [mktoken(1000)]))

    assert not qn.has_tokens(3, query.TOKEN_PARTIAL)
    assert not qn.has_tokens(2, query.TOKEN_COUNTRY)
    assert qn.has_tokens(2, query.TOKEN_PARTIAL)
    assert qn.has_tokens(2, query.TOKEN_WORD)

    assert qn.get_tokens(3, query.TOKEN_PARTIAL) is None
    assert qn.get_tokens(2, query.TOKEN_COUNTRY) is None
    assert len(qn.get_tokens(2, query.TOKEN_PARTIAL)) == 2
    assert len(qn.get_tokens(2, query.TOKEN_WORD)) == 1


def test_query_struct_empty():
    q = query.QueryStruct([])

    assert q.num_token_slots() == 0


def test_query_struct_with_tokens():
    q = query.QueryStruct([query.Phrase(query.PhraseType.NONE, 'foo bar')])
    q.add_node(query.BREAK_WORD, query.PhraseType.NONE)
    q.add_node(query.BREAK_END, query.PhraseType.NONE)

    assert q.num_token_slots() == 2

    q.add_token(query.TokenRange(0, 1), query.TOKEN_PARTIAL, mktoken(1))
    q.add_token(query.TokenRange(1, 2), query.TOKEN_PARTIAL, mktoken(2))
    q.add_token(query.TokenRange(1, 2), query.TOKEN_WORD, mktoken(99))
    q.add_token(query.TokenRange(1, 2), query.TOKEN_WORD, mktoken(98))

    assert q.get_tokens(query.TokenRange(0, 2), query.TOKEN_WORD) == []
    assert len(q.get_tokens(query.TokenRange(1, 2), query.TOKEN_WORD)) == 2

    partials = q.get_partials_list(query.TokenRange(0, 2))

    assert len(partials) == 2
    assert [t.token for t in partials] == [1, 2]

    assert q.find_lookup_word_by_id(4) == 'None'
    assert q.find_lookup_word_by_id(99) == '[W]foo'


def test_query_struct_incompatible_token():
    q = query.QueryStruct([query.Phrase(query.PhraseType.COUNTRY, 'foo bar')])
    q.add_node(query.BREAK_WORD, query.PhraseType.COUNTRY)
    q.add_node(query.BREAK_END, query.PhraseType.NONE)

    q.add_token(query.TokenRange(0, 1), query.TOKEN_PARTIAL, mktoken(1))
    q.add_token(query.TokenRange(1, 2), query.TOKEN_COUNTRY, mktoken(100))

    assert q.get_tokens(query.TokenRange(0, 1), query.TOKEN_PARTIAL) == []
    assert len(q.get_tokens(query.TokenRange(1, 2), query.TOKEN_COUNTRY)) == 1


def test_query_struct_amenity_single_word():
    q = query.QueryStruct([query.Phrase(query.PhraseType.AMENITY, 'bar')])
    q.add_node(query.BREAK_END, query.PhraseType.NONE)

    q.add_token(query.TokenRange(0, 1), query.TOKEN_PARTIAL, mktoken(1))
    q.add_token(query.TokenRange(0, 1), query.TOKEN_NEAR_ITEM, mktoken(2))
    q.add_token(query.TokenRange(0, 1), query.TOKEN_QUALIFIER, mktoken(3))

    assert len(q.get_tokens(query.TokenRange(0, 1), query.TOKEN_PARTIAL)) == 1
    assert len(q.get_tokens(query.TokenRange(0, 1), query.TOKEN_NEAR_ITEM)) == 1
    assert len(q.get_tokens(query.TokenRange(0, 1), query.TOKEN_QUALIFIER)) == 0


def test_query_struct_amenity_two_words():
    q = query.QueryStruct([query.Phrase(query.PhraseType.AMENITY, 'foo bar')])
    q.add_node(query.BREAK_WORD, query.PhraseType.AMENITY)
    q.add_node(query.BREAK_END, query.PhraseType.NONE)

    for trange in [(0, 1), (1, 2)]:
        q.add_token(query.TokenRange(*trange), query.TOKEN_PARTIAL, mktoken(1))
        q.add_token(query.TokenRange(*trange), query.TOKEN_NEAR_ITEM, mktoken(2))
        q.add_token(query.TokenRange(*trange), query.TOKEN_QUALIFIER, mktoken(3))

    assert len(q.get_tokens(query.TokenRange(0, 1), query.TOKEN_PARTIAL)) == 1
    assert len(q.get_tokens(query.TokenRange(0, 1), query.TOKEN_NEAR_ITEM)) == 0
    assert len(q.get_tokens(query.TokenRange(0, 1), query.TOKEN_QUALIFIER)) == 1

    assert len(q.get_tokens(query.TokenRange(1, 2), query.TOKEN_PARTIAL)) == 1
    assert len(q.get_tokens(query.TokenRange(1, 2), query.TOKEN_NEAR_ITEM)) == 0
    assert len(q.get_tokens(query.TokenRange(1, 2), query.TOKEN_QUALIFIER)) == 1

