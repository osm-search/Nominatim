# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for simplified trie structure.
"""

from nominatim_db.tokenizer.token_analysis.simple_trie import SimpleTrie

def test_single_item_trie():
    t = SimpleTrie([('foob', 42)])

    assert t.longest_prefix('afoobar') == (None, 0)
    assert t.longest_prefix('afoobar', start=1) == (42, 5)
    assert t.longest_prefix('foob') == (42, 4)
    assert t.longest_prefix('123foofoo', 3) == (None, 3)

def test_complex_item_tree():
    t = SimpleTrie([('a', 1),
                    ('b', 2),
                    ('auto', 3),
                    ('buto', 4),
                    ('automat', 5),
                    ('bu', 6),
                    ('bx', 7)])

    assert t.longest_prefix('a') == (1, 1)
    assert t.longest_prefix('au') == (1, 1)
    assert t.longest_prefix('aut') == (1, 1)
    assert t.longest_prefix('auto') == (3, 4)
    assert t.longest_prefix('automat') == (5, 7)
    assert t.longest_prefix('automatx') == (5, 7)
    assert t.longest_prefix('butomat') == (4, 4)
    assert t.longest_prefix('butomat', 1) == (None, 1)
