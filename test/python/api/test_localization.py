# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test functions for adapting results to the user's locale.
"""
import pytest

from nominatim_api import Locales


def test_display_name_empty_names():
    loc = Locales(['en', 'de'])

    assert loc.display_name(None) == ''
    assert loc.display_name({}) == ''


def test_display_name_none_localized():
    loc = Locales()

    assert loc.display_name({}) == ''
    assert loc.display_name({'name:de': 'DE', 'name': 'ALL'}) == 'ALL'
    assert loc.display_name({'ref': '34', 'name:de': 'DE'}) == '34'


def test_output_names_none_localized():
    loc = Locales()

    expected_tags = [
        'name', '_place_name', 'brand', '_place_brand', 'official_name', '_place_official_name',
        'short_name', '_place_short_name', 'ref', '_place_ref'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_none_localized_and_custom_output_names(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,entrance:XX,name,brand,test_tag,'
        'official_name:XX,short_name:XX,alt_name:XX'
    )
    loc = Locales()

    expected_tags = [
        'name', '_place_name', 'brand', '_place_brand', 'test_tag', '_place_test_tag'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_none_localized_and_custom_output_names_more_than_two_changes(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,brand,test_tag:XX,official_name,short_name:XX,'
        'alt_name,another_tag_with:XX,another_tag_withoutXX'
    )
    loc = Locales()

    expected_tags = [
        'brand', '_place_brand', 'official_name', '_place_official_name', 'alt_name',
        '_place_alt_name', 'another_tag_withoutXX', '_place_another_tag_withoutXX'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_none_localized_and_custom_output_names_including_space(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,name ,short_name:XX, short_name'
    )
    loc = Locales()

    expected_tags = [
        'name', '_place_name', 'short_name', '_place_short_name'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_display_name_localized():
    loc = Locales(['en', 'de'])

    assert loc.display_name({}) == ''
    assert loc.display_name({'name:de': 'DE', 'name': 'ALL'}) == 'DE'
    assert loc.display_name({'ref': '34', 'name:de': 'DE'}) == 'DE'


def test_output_names_localized():
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name:en', '_place_name:en', 'name:es', '_place_name:es', 'name', '_place_name', 'brand',
        '_place_brand', 'official_name:en', '_place_official_name:en', 'official_name:es',
        '_place_official_name:es', 'short_name:en', '_place_short_name:en', 'short_name:es',
        '_place_short_name:es', 'official_name', '_place_official_name', 'short_name',
        '_place_short_name', 'ref', '_place_ref'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_localized_and_custom_output_names_including_space(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,name ,short_name:XX, short_name'
    )
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name:en', '_place_name:en', 'name:es', '_place_name:es',
        'name', '_place_name',
        'short_name:en', '_place_short_name:en', 'short_name:es', '_place_short_name:es',
        'short_name', '_place_short_name'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_localized_and_custom_output_names(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,entrance:XX,name,brand,test_tag,official_name:XX,short_name:XX,alt_name:XX'
    )
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name:en', '_place_name:en', 'name:es', '_place_name:es', 'entrance:en',
        '_place_entrance:en', 'entrance:es', '_place_entrance:es', 'name', '_place_name',
        'brand', '_place_brand', 'test_tag', '_place_test_tag', 'official_name:en',
        '_place_official_name:en', 'official_name:es', '_place_official_name:es',
        'short_name:en', '_place_short_name:en', 'short_name:es', '_place_short_name:es',
        'alt_name:en', '_place_alt_name:en', 'alt_name:es', '_place_alt_name:es'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_localized_and_custom_output_names_start_with_tag_that_has_no_XX(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name,brand,test_tag,official_name:XX,short_name:XX,alt_name:XX'
    )
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name', '_place_name', 'brand', '_place_brand', 'test_tag', '_place_test_tag',
        'official_name:en', '_place_official_name:en', 'official_name:es',
        '_place_official_name:es', 'short_name:en', '_place_short_name:en', 'short_name:es',
        '_place_short_name:es', 'alt_name:en', '_place_alt_name:en', 'alt_name:es',
        '_place_alt_name:es'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_localized_and_custom_output_names_no_named_tags(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name,brand,test_tag'
    )
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name', '_place_name', 'brand', '_place_brand', 'test_tag', '_place_test_tag'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_localized_and_custom_output_names_only_named_tags(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,entrance:XX,official_name:XX,short_name:XX,alt_name:XX'
    )
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name:en', '_place_name:en', 'name:es', '_place_name:es', 'entrance:en',
        '_place_entrance:en', 'entrance:es', '_place_entrance:es', 'official_name:en',
        '_place_official_name:en', 'official_name:es', '_place_official_name:es',
        'short_name:en', '_place_short_name:en', 'short_name:es', '_place_short_name:es',
        'alt_name:en', '_place_alt_name:en', 'alt_name:es', '_place_alt_name:es'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_localized_and_custom_output_names_more_than_two_changes(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,brand,test_tag:XX,official_name,short_name:XX,'
        'alt_name,another_tag_with:XX,another_tag_withoutXX'
    )
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name:en', '_place_name:en', 'name:es', '_place_name:es', 'brand', '_place_brand',
        'test_tag:en', '_place_test_tag:en', 'test_tag:es', '_place_test_tag:es', 'official_name',
        '_place_official_name', 'short_name:en', '_place_short_name:en', 'short_name:es',
        '_place_short_name:es', 'alt_name', '_place_alt_name', 'another_tag_with:en',
        '_place_another_tag_with:en', 'another_tag_with:es', '_place_another_tag_with:es',
        'another_tag_withoutXX', '_place_another_tag_withoutXX'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_output_names_localized_and_custom_output_names_XX_in_the_middle(monkeypatch):
    monkeypatch.setenv(
        'NOMINATIM_OUTPUT_NAMES',
        'name:XX,br:XXand,test_tag:XX,official_name,sh:XXort_name:XX,'
        'alt_name,another_tag_with:XX,another_tag_withoutXX'
    )
    loc = Locales(['en', 'es'])

    expected_tags = [
        'name:en', '_place_name:en', 'name:es', '_place_name:es', 'br:XXand', '_place_br:XXand',
        'test_tag:en', '_place_test_tag:en', 'test_tag:es', '_place_test_tag:es', 'official_name',
        '_place_official_name', 'sh:XXort_name:en', '_place_sh:XXort_name:en', 'sh:XXort_name:es',
        '_place_sh:XXort_name:es', 'alt_name', '_place_alt_name', 'another_tag_with:en',
        '_place_another_tag_with:en', 'another_tag_with:es', '_place_another_tag_with:es',
        'another_tag_withoutXX', '_place_another_tag_withoutXX'
    ]

    assert loc.name_tags == expected_tags, f'Expected {expected_tags}, but got {loc.name_tags}'


def test_display_name_preference():
    loc = Locales(['en', 'de'])

    assert loc.display_name({}) == ''
    assert loc.display_name({'name:de': 'DE', 'name:en': 'EN'}) == 'EN'
    assert loc.display_name({'official_name:en': 'EN', 'name:de': 'DE'}) == 'DE'


@pytest.mark.parametrize('langstr,langlist',
                         [('fr', ['fr']),
                          ('fr-FR', ['fr-FR', 'fr']),
                          ('de,fr-FR', ['de', 'fr-FR', 'fr']),
                          ('fr,de,fr-FR', ['fr', 'de', 'fr-FR']),
                          ('en;q=0.5,fr', ['fr', 'en']),
                          ('en;q=0.5,fr,en-US', ['fr', 'en-US', 'en']),
                          ('en,fr;garbage,de', ['en', 'de'])])
def test_from_language_preferences(langstr, langlist):
    assert Locales.from_accept_languages(langstr).languages == langlist
