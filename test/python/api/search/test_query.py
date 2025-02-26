# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test data types for search queries.
"""
import pytest

import nominatim_api.search.query as nq

def test_token_range_equal():
    assert nq.TokenRange(2, 3) == nq.TokenRange(2, 3)
    assert not (nq.TokenRange(2, 3) != nq.TokenRange(2, 3))


@pytest.mark.parametrize('lop,rop', [((1, 2), (3, 4)),
                                    ((3, 4), (3, 5)),
                                    ((10, 12), (11, 12))])
def test_token_range_unequal(lop, rop):
    assert not (nq.TokenRange(*lop) == nq.TokenRange(*rop))
    assert nq.TokenRange(*lop) != nq.TokenRange(*rop)


def test_token_range_lt():
    assert nq.TokenRange(1, 3) < nq.TokenRange(10, 12)
    assert nq.TokenRange(5, 6) < nq.TokenRange(7, 8)
    assert nq.TokenRange(1, 4) < nq.TokenRange(4, 5)
    assert not(nq.TokenRange(5, 6) < nq.TokenRange(5, 6))
    assert not(nq.TokenRange(10, 11) < nq.TokenRange(4, 5))


def test_token_rankge_gt():
    assert nq.TokenRange(3, 4) > nq.TokenRange(1, 2)
    assert nq.TokenRange(100, 200) > nq.TokenRange(10, 11)
    assert nq.TokenRange(10, 11) > nq.TokenRange(4, 10)
    assert not(nq.TokenRange(5, 6) > nq.TokenRange(5, 6))
    assert not(nq.TokenRange(1, 2) > nq.TokenRange(3, 4))
    assert not(nq.TokenRange(4, 10) > nq.TokenRange(3, 5))


def test_token_range_unimplemented_ops():
    with pytest.raises(TypeError):
        nq.TokenRange(1, 3) <= nq.TokenRange(10, 12)
    with pytest.raises(TypeError):
        nq.TokenRange(1, 3) >= nq.TokenRange(10, 12)


def test_query_extract_words():
    q = nq.QueryStruct([])
    q.add_node(nq.BREAK_WORD, nq.PHRASE_ANY, 0.1, '12', '')
    q.add_node(nq.BREAK_TOKEN, nq.PHRASE_ANY, 0.0, 'ab', '')
    q.add_node(nq.BREAK_PHRASE, nq.PHRASE_ANY, 0.0, '12', '')
    q.add_node(nq.BREAK_END, nq.PHRASE_ANY, 0.5, 'hallo', '')

    words = q.extract_words(base_penalty=1.0)

    assert set(words.keys()) \
             == {'12', 'ab', 'hallo', '12 ab', 'ab 12', '12 ab 12'}
    assert sorted(words['12']) == [nq.TokenRange(0, 1, 1.0), nq.TokenRange(2, 3, 1.0)]
    assert words['12 ab'] == [nq.TokenRange(0, 2, 1.1)]
    assert words['hallo'] == [nq.TokenRange(3, 4, 1.0)]

