# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that splits multivalue lists.
"""
import pytest

from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.data.place_info import PlaceInfo

from nominatim.errors import UsageError

class TestSplitName:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config


    def run_sanitizer_on(self, **kwargs):
        place = PlaceInfo({'name': kwargs})
        name, _ = PlaceSanitizer([{'step': 'split-name-list'}], self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix) for p in name])


    def sanitize_with_delimiter(self, delimiter, name):
        place = PlaceInfo({'name': {'name': name}})
        san = PlaceSanitizer([{'step': 'split-name-list', 'delimiters': delimiter}],
                             self.config)
        name, _ = san.process_names(place)

        return sorted([p.name for p in name])


    def test_simple(self):
        assert self.run_sanitizer_on(name='ABC') == [('ABC', 'name', None)]
        assert self.run_sanitizer_on(name='') == [('', 'name', None)]


    def test_splits(self):
        assert self.run_sanitizer_on(name='A;B;C') == [('A', 'name', None),
                                                       ('B', 'name', None),
                                                       ('C', 'name', None)]
        assert self.run_sanitizer_on(short_name=' House, boat ') == [('House', 'short_name', None),
                                                                     ('boat', 'short_name', None)]


    def test_empty_fields(self):
        assert self.run_sanitizer_on(name='A;;B') == [('A', 'name', None),
                                                      ('B', 'name', None)]
        assert self.run_sanitizer_on(name='A; ,B') == [('A', 'name', None),
                                                       ('B', 'name', None)]
        assert self.run_sanitizer_on(name=' ;B') == [('B', 'name', None)]
        assert self.run_sanitizer_on(name='B,') == [('B', 'name', None)]


    def test_custom_delimiters(self):
        assert self.sanitize_with_delimiter(':', '12:45,3') == ['12', '45,3']
        assert self.sanitize_with_delimiter('\\', 'a;\\b!#@ \\') == ['a;', 'b!#@']
        assert self.sanitize_with_delimiter('[]', 'foo[to]be') == ['be', 'foo', 'to']
        assert self.sanitize_with_delimiter(' ', 'morning  sun') == ['morning', 'sun']


    def test_empty_delimiter_set(self):
        with pytest.raises(UsageError):
            self.sanitize_with_delimiter('', 'abc')


def test_no_name_list(def_config):
    place = PlaceInfo({'address': {'housenumber': '3'}})
    name, address = PlaceSanitizer([{'step': 'split-name-list'}], def_config).process_names(place)

    assert not name
    assert len(address) == 1
