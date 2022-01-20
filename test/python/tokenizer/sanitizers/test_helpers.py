# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for sanitizer helper functions.
"""
import pytest

from nominatim.errors import UsageError
from nominatim.tokenizer.place_sanitizer import PlaceName
import nominatim.tokenizer.sanitizers.helpers as helpers

@pytest.mark.parametrize('inp', ('fg34', 'f\\f', 'morning [glory]', '56.78'))
def test_create_split_regex_no_params_unsplit(inp):
    regex = helpers.create_split_regex({})

    assert list(regex.split(inp)) == [inp]


@pytest.mark.parametrize('inp,outp', [('here,there', ['here', 'there']),
                                      ('ying;;yang', ['ying', 'yang']),
                                      (';a; ;c;d,', ['', 'a', '', 'c', 'd', '']),
                                      ('1,  3  ,5', ['1', '3', '5'])
                                     ])
def test_create_split_regex_no_params_split(inp, outp):
    regex = helpers.create_split_regex({})

    assert list(regex.split(inp)) == outp


@pytest.mark.parametrize('delimiter', ['.', '\\', '[]', '   ', '/.*+'])
def test_create_split_regex_custom(delimiter):
    regex = helpers.create_split_regex({'delimiters': delimiter})

    assert list(regex.split(f'out{delimiter}house')) == ['out', 'house']
    assert list(regex.split('out,house')) == ['out,house']


def test_create_split_regex_empty_delimiter():
    with pytest.raises(UsageError):
        regex = helpers.create_split_regex({'delimiters': ''})


@pytest.mark.parametrize('inp', ('name', 'name:de', 'na\\me', '.*'))
def test_create_kind_filter_no_params(inp):
    filt = helpers.create_kind_filter({})

    assert filt(PlaceName('something', inp, ''))


@pytest.mark.parametrize('kind', ('de', 'name:de', 'ende'))
def test_create_kind_filter_custom_regex_positive(kind):
    filt = helpers.create_kind_filter({'filter-kind': '.*de'})

    assert filt(PlaceName('something', kind, ''))


@pytest.mark.parametrize('kind', ('de ', '123', '', 'bedece'))
def test_create_kind_filter_custom_regex_negative(kind):
    filt = helpers.create_kind_filter({'filter-kind': '.*de'})

    assert not filt(PlaceName('something', kind, ''))


@pytest.mark.parametrize('kind', ('name', 'fr', 'name:fr', 'frfr', '34'))
def test_create_kind_filter_many_positive(kind):
    filt = helpers.create_kind_filter({'filter-kind': ['.*fr', 'name', r'\d+']})

    assert filt(PlaceName('something', kind, ''))


@pytest.mark.parametrize('kind', ('name:de', 'fridge', 'a34', '.*', '\\'))
def test_create_kind_filter_many_negative(kind):
    filt = helpers.create_kind_filter({'filter-kind': ['.*fr', 'name', r'\d+']})

    assert not filt(PlaceName('something', kind, ''))
