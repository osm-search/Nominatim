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
