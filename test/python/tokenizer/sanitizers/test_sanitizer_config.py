# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for sanitizer configuration helper functions.
"""
import pytest

from nominatim.errors import UsageError
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

def test_string_list_default_empty():
    assert SanitizerConfig().get_string_list('op') == []


def test_string_list_default_something():
    assert SanitizerConfig().get_string_list('op', default=['a', 'b']) == ['a', 'b']


def test_string_list_value_string():
    assert SanitizerConfig({'op': 't'}).get_string_list('op', default=['a', 'b']) == ['t']


def test_string_list_value_list():
    assert SanitizerConfig({'op': ['1', '2']}).get_string_list('op') == ['1', '2']


def test_string_list_value_empty():
    assert SanitizerConfig({'op': ''}).get_string_list('op', default=['a', 'b']) == []


def test_string_list_value_dict():
    with pytest.raises(UsageError):
        SanitizerConfig({'op': {'1': 'a'}}).get_string_list('op')


def test_string_list_value_int_list():
    with pytest.raises(UsageError):
        SanitizerConfig({'op': [1, 2]}).get_string_list('op')


@pytest.mark.parametrize('inp', ('fg34', 'f\\f', 'morning [glory]', '56.78'))
def test_create_split_regex_no_params_unsplit(inp):
    regex = SanitizerConfig().get_delimiter()

    assert list(regex.split(inp)) == [inp]


@pytest.mark.parametrize('inp,outp', [('here,there', ['here', 'there']),
                                      ('ying;;yang', ['ying', 'yang']),
                                      (';a; ;c;d,', ['', 'a', '', 'c', 'd', '']),
                                      ('1,  3  ,5', ['1', '3', '5'])
                                     ])
def test_create_split_regex_no_params_split(inp, outp):
    regex = SanitizerConfig().get_delimiter()

    assert list(regex.split(inp)) == outp


@pytest.mark.parametrize('delimiter', ['.', '\\', '[]', '   ', '/.*+'])
def test_create_split_regex_custom(delimiter):
    regex = SanitizerConfig({'delimiters': delimiter}).get_delimiter()

    assert list(regex.split(f'out{delimiter}house')) == ['out', 'house']
    assert list(regex.split('out,house')) == ['out,house']


def test_create_split_regex_empty_delimiter():
    with pytest.raises(UsageError):
        regex = SanitizerConfig({'delimiters': ''}).get_delimiter()


@pytest.mark.parametrize('inp', ('name', 'name:de', 'na\\me', '.*', ''))
def test_create_name_filter_no_param_no_default(inp):
    filt = SanitizerConfig({'filter-kind': 'place'}).get_filter('name')

    assert filt(inp)


@pytest.mark.parametrize('inp', ('name', 'name:de', 'na\\me', '.*', ''))
def test_create_name_filter_no_param_default_pass_all(inp):
    filt = SanitizerConfig().get_filter('name', 'PASS_ALL')

    assert filt(inp)


@pytest.mark.parametrize('inp', ('name', 'name:de', 'na\\me', '.*', ''))
def test_create_name_filter_no_param_default_fail_all(inp):
    filt = SanitizerConfig().get_filter('name', 'FAIL_ALL')

    assert not filt(inp)


def test_create_name_filter_no_param_default_invalid_string():
    with pytest.raises(ValueError):
        filt = SanitizerConfig().get_filter('name', 'abc')


def test_create_name_filter_no_param_default_empty_list():
    with pytest.raises(ValueError):
        filt = SanitizerConfig().get_filter('name', [])


@pytest.mark.parametrize('kind', ('de', 'name:de', 'ende'))
def test_create_kind_filter_default_positive(kind):
    filt = SanitizerConfig().get_filter('filter-kind', ['.*de'])

    assert filt(kind)


@pytest.mark.parametrize('kind', ('de', 'name:de', 'ende'))
def test_create_kind_filter_default_negetive(kind):
    filt = SanitizerConfig().get_filter('filter-kind', ['.*fr'])

    assert not filt(kind)


@pytest.mark.parametrize('kind', ('lang', 'lang:de', 'langxx'))
def test_create_kind_filter_custom_regex_positive(kind):
    filt = SanitizerConfig({'filter-kind': 'lang.*'}
    ).get_filter('filter-kind', ['.*fr'])

    assert filt(kind)


@pytest.mark.parametrize('kind', ('de ', '123', '', 'bedece'))
def test_create_kind_filter_custom_regex_negative(kind):
    filt = SanitizerConfig({'filter-kind': '.*de'}).get_filter('filter-kind')

    assert not filt(kind)


@pytest.mark.parametrize('kind', ('name', 'fr', 'name:fr', 'frfr', '34'))
def test_create_kind_filter_many_positive(kind):
    filt = SanitizerConfig({'filter-kind': ['.*fr', 'name', r'\d+']}
    ).get_filter('filter-kind')

    assert filt(kind)


@pytest.mark.parametrize('kind', ('name:de', 'fridge', 'a34', '.*', '\\'))
def test_create_kind_filter_many_negative(kind):
    filt = SanitizerConfig({'filter-kind': ['.*fr', 'name', r'\d+']}
    ).get_filter('filter-kind')

    assert not filt(kind)
