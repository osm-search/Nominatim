# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that creates derived names using regular expressions.
"""
import pytest

from nominatim_db.errors import UsageError
from nominatim_db.data.place_info import PlaceInfo
from nominatim_db.tokenizer.place_sanitizer import PlaceSanitizer


@pytest.fixture
def mk_sanitizer(def_config):
    def _f(**kwargs):
        args = {k.replace('_', '-'): v for k, v in kwargs.items()}
        return PlaceSanitizer([args | {'step': 'derive-names'}], def_config)

    return _f


def test_no_parameters(mk_sanitizer):
    with pytest.raises(UsageError, match='name-pattern is missing'):
        mk_sanitizer()


@pytest.mark.parametrize('prim,out', [('name', 0), ('address', 1)])
@pytest.mark.parametrize('keep', [True, False])
def test_name_deletion(mk_sanitizer, prim, out, keep):
    san = mk_sanitizer(name_pattern='A.*B', type=prim, keep_original=keep)

    names = dict(name='AltBoom', alt_name='foo', loc_name='AltB')
    place = PlaceInfo({'name': names, 'address': names,
                       'country_code': 'de', 'rank_address': 30})

    san.process_names(place)
    res = [place.sanitized_names, place.sanitized_address]

    assert len(res[(out + 1) % 2]) == 3
    if keep:
        assert len(res[out]) == 3
    else:
        assert {(p.kind, p.name) for p in res[out]} == {('name', 'AltBoom'),
                                                        ('alt_name', 'foo')}


@pytest.fixture
def simple_replace(mk_sanitizer):
    def _impl(name, pattern, *variants, keep=True):
        san = mk_sanitizer(name_pattern=pattern, type='name', keep_original=keep,
                           variants=variants)
        place = PlaceInfo({'name': {'name': name}, 'country_code': 'de', 'rank_address': 30})
        san.process_names(place)

        return {p.name for p in place.sanitized_names}
    return _impl


def test_variant_single_name(simple_replace):
    assert simple_replace('A', 'A', 'The A') == {'A', 'The A'}


def test_replace_single_name(simple_replace):
    assert simple_replace('A', 'A', 'The A', keep=False) == {'The A'}


def test_variant_with_multiple_names(simple_replace):
    assert simple_replace('A', 'A', 'A1', 'A2', 'A1') == {'A', 'A1', 'A2'}


def test_variant_with_group_replacement(simple_replace):
    assert simple_replace('abc X', '(.*) X', r'\1 Y') == {'abc X', 'abc Y'}
