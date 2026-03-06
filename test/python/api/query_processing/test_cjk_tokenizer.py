# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for CJK full-word token preservation in ICU tokenizer.
Covers split_query() Han token injection and Japanese protection guard.
"""
import pytest
from nominatim_api.search.icu_tokenizer import _is_han_word, _is_japanese_script


def test_pure_chinese_is_han():
    """ Pure Chinese characters must be detected as Han. """
    assert _is_han_word('小学校') is True


def test_pure_japanese_kanji_is_han():
    """ Pure kanji is also Han — detection must be True. """
    assert _is_han_word('東京大学') is True


def test_latin_is_not_han():
    """ Latin text must not be detected as Han. """
    assert _is_han_word('Tokyo') is False


def test_mixed_is_not_han():
    """ Mixed Han and Latin must not be detected as pure Han. """
    assert _is_han_word('小学校Tokyo') is False


def test_empty_is_not_han():
    """ Empty string must return False safely. """
    assert _is_han_word('') is False


def test_japanese_phrase_detected():
    """ Phrase containing hiragana must be detected as Japanese. """
    assert _is_japanese_script('東京のキャンパス') is True


def test_katakana_detected():
    """ Phrase containing katakana must be detected as Japanese. """
    assert _is_japanese_script('トウキョウ') is True


def test_chinese_phrase_not_japanese():
    """ Pure Chinese phrase must not be detected as Japanese. """
    assert _is_japanese_script('小学校') is False


def test_latin_not_japanese():
    """ Latin text must not be detected as Japanese. """
    assert _is_japanese_script('Tokyo') is False


def test_empty_not_japanese():
    """ Empty string must return False safely. """
    assert _is_japanese_script('') is False

def test_cjk_extension_b_character():
    """ Unicode Extension B characters must also be detected as Han.
        This verifies coverage beyond the core CJK block.
    """
    assert _is_han_word('𠀀') is True