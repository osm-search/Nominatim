# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test functions for adapting results to the user's locale.
"""
import pytest

from nominatim_api import Locales

def test_display_name_empty_names():
    l = Locales(['en', 'de'])

    assert l.display_name(None) == ''
    assert l.display_name({}) == ''

def test_display_name_none_localized():
    l = Locales()

    assert l.display_name({}) == ''
    assert l.display_name({'name:de': 'DE', 'name': 'ALL'}) == 'ALL'
    assert l.display_name({'ref': '34', 'name:de': 'DE'}) == '34'


def test_display_name_localized():
    l = Locales(['en', 'de'])

    assert l.display_name({}) == ''
    assert l.display_name({'name:de': 'DE', 'name': 'ALL'}) == 'DE'
    assert l.display_name({'ref': '34', 'name:de': 'DE'}) == 'DE'


def test_display_name_preference():
    l = Locales(['en', 'de'])

    assert l.display_name({}) == ''
    assert l.display_name({'name:de': 'DE', 'name:en': 'EN'}) == 'EN'
    assert l.display_name({'official_name:en': 'EN', 'name:de': 'DE'}) == 'DE'


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


def test_configurable_output_name_tags():
    """
    tests the output name tags when environment config is provided
    """
    name_tags = [
        "name:en",
        "_place_name:en",
        "name",
        "_place_name",
        "brand",
        "_place_brand",
        "official_name:en",
        "_place_official_name:en",
        "shirt_name:en",
        "_place_shirt_name:en",
        "official_name",
        "_place_official_name",
        "shirt_name",
        "_place_shirt_name",
        "ref",
        "_place_ref",
    ]
    l = Locales(
        ['en'],
        output_name_tags_config=(
            "name:XX,name,brand,official_name:XX,shirt_name:XX,official_name,shirt_name,ref"
        )
    )
    assert l.name_tags == name_tags


def test_default_output_name_tags():
    """
    tests the default setting (previously hardcoded) in case environment config is not provided
    """
    name_tags = [
        "name",
        "_place_name",
        "brand",
        "_place_brand",
        "official_name",
        "_place_official_name",
        "short_name",
        "_place_short_name",
        "ref",
        "_place_ref",
    ]
    l = Locales()
    assert l.name_tags == name_tags
