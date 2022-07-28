# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that handles braced suffixes.
"""
import pytest

from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.data.place_info import PlaceInfo

class TestStripBrace:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, **kwargs):
        place = PlaceInfo({'name': kwargs})
        name, _ = PlaceSanitizer([{'step': 'strip-brace-terms'}], self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix) for p in name])


    def test_no_braces(self):
        assert self.run_sanitizer_on(name='foo', ref='23') == [('23', 'ref', None),
                                                               ('foo', 'name', None)]


    def test_simple_braces(self):
        assert self.run_sanitizer_on(name='Halle (Saale)', ref='3')\
          == [('3', 'ref', None), ('Halle', 'name', None), ('Halle (Saale)', 'name', None)]
        assert self.run_sanitizer_on(name='ack ( bar')\
          == [('ack', 'name', None), ('ack ( bar', 'name', None)]


    def test_only_braces(self):
        assert self.run_sanitizer_on(name='(maybe)') == [('(maybe)', 'name', None)]


    def test_double_braces(self):
        assert self.run_sanitizer_on(name='a((b))') == [('a', 'name', None),
                                                        ('a((b))', 'name', None)]
        assert self.run_sanitizer_on(name='a (b) (c)') == [('a', 'name', None),
                                                           ('a (b) (c)', 'name', None)]


def test_no_names(def_config):
    place = PlaceInfo({'address': {'housenumber': '3'}})
    name, address = PlaceSanitizer([{'step': 'strip-brace-terms'}], def_config).process_names(place)

    assert not name
    assert len(address) == 1
