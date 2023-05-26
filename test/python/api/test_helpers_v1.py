# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the helper functions for v1 API.
"""
import pytest

import nominatim.api.v1.helpers as helper

@pytest.mark.parametrize('inp', ['', 'abc', '12 23', 'abc -78.90, 12.456 def'])
def test_extract_coords_no_coords(inp):
    query, x, y = helper.extract_coords_from_query(inp)

    assert query == inp
    assert x is None
    assert y is None


def test_extract_coords_null_island():
    assert ('', 0.0, 0.0) == helper.extract_coords_from_query('0.0 -0.0')


def test_extract_coords_with_text_before():
    assert ('abc', 12.456, -78.90) == helper.extract_coords_from_query('abc  -78.90, 12.456')


def test_extract_coords_with_text_after():
    assert ('abc', 12.456, -78.90) == helper.extract_coords_from_query('-78.90, 12.456   abc')

@pytest.mark.parametrize('inp', [' [12.456,-78.90] ', ' 12.456,-78.90 '])
def test_extract_coords_with_spaces(inp):
    assert ('', -78.90, 12.456) == helper.extract_coords_from_query(inp)

@pytest.mark.parametrize('inp', ['40 26.767 N 79 58.933 W',
                     '40° 26.767′ N 79° 58.933′ W',
                     "40° 26.767' N 79° 58.933' W",
                     "40° 26.767'\n"
                     "    N 79° 58.933' W",
                     'N 40 26.767, W 79 58.933',
                     'N 40°26.767′, W 79°58.933′',
                     '	N 40°26.767′, W 79°58.933′',
                     "N 40°26.767', W 79°58.933'",
 
                     '40 26 46 N 79 58 56 W',
                     '40° 26′ 46″ N 79° 58′ 56″ W',
                     '40° 26′ 46.00″ N 79° 58′ 56.00″ W',
                     '40°26′46″N 79°58′56″W',
                     'N 40 26 46 W 79 58 56',
                     'N 40° 26′ 46″, W 79° 58′ 56″',
                     'N 40° 26\' 46", W 79° 58\' 56"',
                     'N 40° 26\' 46", W 79° 58\' 56"',
 
                     '40.446 -79.982',
                     '40.446,-79.982',
                     '40.446° N 79.982° W',
                     'N 40.446° W 79.982°',
 
                     '[40.446 -79.982]',
                     '[40.446,-79.982]',
                     '       40.446  ,   -79.982     ',
                     '       40.446  ,   -79.982     ',
                     '       40.446	,   -79.982	',
                     '       40.446,   -79.982	'])
def test_extract_coords_formats(inp):
    query, x, y = helper.extract_coords_from_query(inp)

    assert query == ''
    assert pytest.approx(x, abs=0.001) == -79.982
    assert pytest.approx(y, abs=0.001) == 40.446

    query, x, y = helper.extract_coords_from_query('foo bar ' + inp)

    assert query == 'foo bar'
    assert pytest.approx(x, abs=0.001) == -79.982
    assert pytest.approx(y, abs=0.001) == 40.446

    query, x, y = helper.extract_coords_from_query(inp + ' x')

    assert query == 'x'
    assert pytest.approx(x, abs=0.001) == -79.982
    assert pytest.approx(y, abs=0.001) == 40.446


def test_extract_coords_formats_southeast():
    query, x, y = helper.extract_coords_from_query('S 40 26.767, E 79 58.933')

    assert query == ''
    assert pytest.approx(x, abs=0.001) == 79.982
    assert pytest.approx(y, abs=0.001) == -40.446


@pytest.mark.parametrize('inp', ['[shop=fish] foo bar',
                                 'foo [shop=fish] bar',
                                 'foo [shop=fish]bar',
                                 'foo bar [shop=fish]'])
def test_extract_category_good(inp):
    query, cls, typ = helper.extract_category_from_query(inp)

    assert query == 'foo bar'
    assert cls == 'shop'
    assert typ == 'fish'

def test_extract_category_only():
    assert helper.extract_category_from_query('[shop=market]') == ('', 'shop', 'market')

@pytest.mark.parametrize('inp', ['house []', 'nothing', '[352]'])
def  test_extract_category_no_match(inp):
    assert helper.extract_category_from_query(inp) == (inp, None, None)
