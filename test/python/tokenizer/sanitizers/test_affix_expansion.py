# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that expands prefixes and suffixes.
"""
import pytest

from nominatim_db.data.place_info import PlaceInfo
from nominatim_db.tokenizer.place_sanitizer import PlaceSanitizer


@pytest.fixture
def run_sanitizer(def_config):
    def _f(place, **kwargs):
        args = {k.replace('_', '-'): v for k, v in kwargs.items()}
        PlaceSanitizer([args | {'step': 'affix-expansion'}], def_config).process_names(place)
        nameset = {(p.name, p.kind, p.suffix) for p in place.sanitized_names}
        assert len(place.sanitized_names) == len(nameset)
        return nameset

    return _f


def mk_place(names):
    return PlaceInfo({'name': names, 'country_code': 'de', 'rank_address': 30})


def test_default_settings(run_sanitizer):
    place = mk_place({'name': 'Foo Street', 'name:prefix': 'North',
                      'alt_name': 'Foo Street South', 'alt_name:suffix': 'South',
                      'loc_name': 'Fun Mile'})

    assert run_sanitizer(place) == {('Foo Street', 'name', None),
                                    ('North Foo Street', 'name', None),
                                    ('Foo Street South', 'alt_name', None),
                                    ('Foo Street', 'alt_name', None),
                                    ('Fun Mile', 'loc_name', None)}


def test_custom_prefix(run_sanitizer):
    place = mk_place({'name': 'Foo Street', 'name:start': 'North',
                      'name:fr': 'West Bubble Street', 'name:begin:fr': 'West',
                      'name:prefix': 'other'})

    assert run_sanitizer(place, prefix_tags=['start', 'begin']) == \
        {('Foo Street', 'name', None),
         ('North Foo Street', 'name', None),
         ('West Bubble Street', 'name', 'fr'),
         ('Bubble Street', 'name', 'fr'),
         ('other', 'name', 'prefix')}


def test_custom_suffix(run_sanitizer):
    place = mk_place({'name': 'Foo Street', 'name:end': 'B',
                      'alt_name': 'Balula', 'alt_name:final': 'Loo',
                      'name:de': 'H', 'name:de:prefix': 'N'})

    assert run_sanitizer(place, suffix_tags=['end', 'final']) == \
        {('Foo Street', 'name', None),
         ('Foo Street B', 'name', None),
         ('Balula', 'alt_name', None),
         ('Balula Loo', 'alt_name', None),
         ('H', 'name', 'de'),
         ('N H', 'name', 'de')}


@pytest.mark.parametrize('stem', ['Stem Road', 'Pre Stem Road',
                                  'Stem Road Post', 'Pre Stem Road Post'])
def test_prefix_and_suffix_given(run_sanitizer, stem):
    place = mk_place({'name': stem, 'name:prefix': 'Pre', 'name:suffix': 'Post'})

    assert run_sanitizer(place, mode='full-name') == \
        {('Pre Stem Road Post', 'name', None)}
    assert run_sanitizer(place, mode='short-name') == \
        {('Stem Road', 'name', None), ('Pre', 'prefix', None), ('Post', 'suffix', None)}


def test_modes_full_name_given(run_sanitizer):
    place = mk_place({'name': 'Full Name Street', 'name:prefix': 'Full'})

    assert run_sanitizer(place, mode='full-name') == \
        {('Full Name Street', 'name', None)}
    assert run_sanitizer(place, mode='short-name') == \
        {('Name Street', 'name', None), ('Full', 'prefix', None)}
    assert run_sanitizer(place, mode='all-variants') == \
        {('Full Name Street', 'name', None), ('Name Street', 'name', None)}
    assert run_sanitizer(place, mode='add-expanded') == \
        {('Full Name Street', 'name', None)}
    assert run_sanitizer(place, mode='add-contracted') == \
        {('Full Name Street', 'name', None), ('Name Street', 'name', None)}


def test_modes_short_name_given(run_sanitizer):
    place = mk_place({'name': 'My Street', 'name:suffix': 'extra'})

    assert run_sanitizer(place, mode='full-name') == \
        {('My Street extra', 'name', None)}
    assert run_sanitizer(place, mode='short-name') == \
        {('My Street', 'name', None), ('extra', 'suffix', None)}
    assert run_sanitizer(place, mode='all-variants') == \
        {('My Street extra', 'name', None), ('My Street', 'name', None)}
    assert run_sanitizer(place, mode='add-expanded') == \
        {('My Street extra', 'name', None), ('My Street', 'name', None)}
    assert run_sanitizer(place, mode='add-contracted') == \
        {('My Street', 'name', None)}
