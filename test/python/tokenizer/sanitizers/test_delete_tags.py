# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that normalizes housenumbers.
"""
import pytest


from nominatim.data.place_info import PlaceInfo
from nominatim.tokenizer.place_sanitizer import PlaceSanitizer


class TestWithDefault:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, type, **kwargs):

        place = PlaceInfo({type: {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'de', 'rank_address': 30})

        sanitizer_args = {'step': 'delete-tags'}

        name, address = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return {
                'name': sorted([(p.name, p.kind, p.suffix or '') for p in name]),
                'address': sorted([(p.name, p.kind, p.suffix or '') for p in address])
            }


    def test_on_name(self):
        res = self.run_sanitizer_on('name', name='foo', ref='bar', ref_abc='baz')

        assert res.get('name') == []

    def test_on_address(self):
        res = self.run_sanitizer_on('address', name='foo', ref='bar', ref_abc='baz')

        assert res.get('address') == [('bar', 'ref', ''), ('baz', 'ref', 'abc'),
                                        ('foo', 'name', '')]


class TestTypeField:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, type, **kwargs):

        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'de', 'rank_address': 30})

        sanitizer_args = {
                        'step': 'delete-tags',
                        'type': type,
                    }

        name, _ = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix or '') for p in name])

    def test_name_type(self):
        res = self.run_sanitizer_on('name', name='foo', ref='bar', ref_abc='baz')

        assert res == []

    def test_address_type(self):
        res = self.run_sanitizer_on('address', name='foo', ref='bar', ref_abc='baz')

        assert res == [('bar', 'ref', ''), ('baz', 'ref', 'abc'),
                        ('foo', 'name', '')]

class TestFilterKind:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, filt, **kwargs):

        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'de', 'rank_address': 30})

        sanitizer_args = {
                        'step': 'delete-tags',
                        'filter-kind': filt,
                    }

        name, _ = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix or '') for p in name])

    def test_single_exact_name(self):
        res = self.run_sanitizer_on(['name'], ref='foo', name='foo',
                                    name_abc='bar', ref_abc='bar')

        assert res == [('bar', 'ref', 'abc'), ('foo', 'ref', '')]


    def test_single_pattern(self):
        res = self.run_sanitizer_on(['.*name'],
                                    name_fr='foo', ref_fr='foo', namexx_fr='bar',
                                    shortname_fr='bar', name='bar')

        assert res == [('bar', 'namexx', 'fr'), ('foo', 'ref', 'fr')]


    def test_multiple_patterns(self):
        res = self.run_sanitizer_on(['.*name', 'ref'],
                                    name_fr='foo', ref_fr='foo', oldref_fr='foo',
                                    namexx_fr='bar', shortname_fr='baz', name='baz')

        assert res == [('bar', 'namexx', 'fr'), ('foo', 'oldref', 'fr')]


class TestRankAddress:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, rank_addr, **kwargs):

        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'de', 'rank_address': 30})

        sanitizer_args = {
                        'step': 'delete-tags',
                        'rank_address': rank_addr
                    }

        name, _ = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix or '') for p in name])


    def test_single_rank(self):
        res = self.run_sanitizer_on('30', name='foo', ref='bar')

        assert res == []

    def test_single_rank_fail(self):
        res = self.run_sanitizer_on('28', name='foo', ref='bar')

        assert res == [('bar', 'ref', ''), ('foo', 'name', '')]

    def test_ranged_rank_pass(self):
        res = self.run_sanitizer_on('26-30', name='foo', ref='bar')

        assert res == []

    def test_ranged_rank_fail(self):
        res = self.run_sanitizer_on('26-29', name='foo', ref='bar')

        assert res == [('bar', 'ref', ''), ('foo', 'name', '')]

    def test_mixed_rank_pass(self):
        res = self.run_sanitizer_on(['4', '20-28', '30', '10-12'], name='foo', ref='bar')

        assert res == []

    def test_mixed_rank_fail(self):
        res = self.run_sanitizer_on(['4-8', '10', '26-29', '18'], name='foo', ref='bar')

        assert res == [('bar', 'ref', ''), ('foo', 'name', '')]


class TestSuffix:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, suffix, **kwargs):

        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'de', 'rank_address': 30})

        sanitizer_args = {
                        'step': 'delete-tags',
                        'suffix': suffix,
                    }

        name, _ = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix or '') for p in name])


    def test_single_suffix(self):
        res = self.run_sanitizer_on('abc', name='foo', name_abc='foo',
                                 name_pqr='bar', ref='bar', ref_abc='baz')

        assert res == [('bar', 'name', 'pqr'), ('bar', 'ref', ''), ('foo', 'name', '')]

    def test_multiple_suffix(self):
        res = self.run_sanitizer_on(['abc.*', 'pqr'], name='foo', name_abcxx='foo',
                                 ref_pqr='bar', name_pqrxx='baz')

        assert res == [('baz', 'name', 'pqrxx'), ('foo', 'name', '')]



class TestCountryCodes:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, country_code, **kwargs):

        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'de', 'rank_address': 30})

        sanitizer_args = {
                        'step': 'delete-tags',
                        'country_code': country_code,
                    }

        name, _ = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return sorted([(p.name, p.kind) for p in name])


    def test_single_country_code_pass(self):
        res = self.run_sanitizer_on('de', name='foo', ref='bar')

        assert res == []

    def test_single_country_code_fail(self):
        res = self.run_sanitizer_on('in', name='foo', ref='bar')

        assert res == [('bar', 'ref'), ('foo', 'name')]

    def test_empty_country_code_list(self):
        res = self.run_sanitizer_on([], name='foo', ref='bar')

        assert res == [('bar', 'ref'), ('foo', 'name')]

    def test_multiple_country_code_pass(self):
        res = self.run_sanitizer_on(['in', 'de', 'fr'], name='foo', ref='bar')

        assert res == []

    def test_multiple_country_code_fail(self):
        res = self.run_sanitizer_on(['in', 'au', 'fr'], name='foo', ref='bar')

        assert res == [('bar', 'ref'), ('foo', 'name')]

class TestAllParameters:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config

    def run_sanitizer_on(self, country_code, rank_addr, suffix, **kwargs):

        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                            'country_code': 'de', 'rank_address': 30})

        sanitizer_args = {
                        'step': 'delete-tags',
                        'type': 'name',
                        'filter-kind': ['name', 'ref'],
                        'country_code': country_code,
                        'rank_address': rank_addr,
                        'suffix': suffix,
                        'name': r'[\s\S]*',
                    }

        name, _ = PlaceSanitizer([sanitizer_args],
                                    self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix or '') for p in name])


    def test_string_arguments_pass(self):
        res = self.run_sanitizer_on('de', '25-30', r'[\s\S]*',
                                    name='foo', ref='foo', name_abc='bar', ref_abc='baz')

        assert res == []

    def test_string_arguments_fail(self):
        res = self.run_sanitizer_on('in', '25-30', r'[\s\S]*',
                                    name='foo', ref='foo', name_abc='bar', ref_abc='baz')

        assert res == [('bar', 'name', 'abc'), ('baz', 'ref', 'abc'),
                       ('foo', 'name', ''), ('foo', 'ref', '')]

    def test_list_arguments_pass(self):
        res = self.run_sanitizer_on(['de', 'in'], ['20-28', '30'], [r'abc.*', r'[\s\S]*'],
                                    name='foo', ref_abc='foo', name_abcxx='bar', ref_pqr='baz')

        assert res == []

    def test_list_arguments_fail(self):
        res = self.run_sanitizer_on(['de', 'in'], ['14', '20-29'], [r'abc.*', r'pqr'],
                                    name='foo', ref_abc='foo', name_abcxx='bar', ref_pqr='baz')

        assert res == [('bar', 'name', 'abcxx'), ('baz', 'ref', 'pqr'),
                       ('foo', 'name', ''), ('foo', 'ref', 'abc')]

    def test_mix_arguments_pass(self):
        res = self.run_sanitizer_on('de', ['10', '20-28', '30'], r'[\s\S]*',
                                    name='foo', ref_abc='foo', name_abcxx='bar', ref_pqr='baz')

        assert res == []

    def test_mix_arguments_fail(self):
        res = self.run_sanitizer_on(['de', 'in'], ['10', '20-28', '30'], r'abc.*',
                                    name='foo', ref='foo', name_pqr='bar', ref_pqr='baz')

        assert res == [('bar', 'name', 'pqr'), ('baz', 'ref', 'pqr'),
                       ('foo', 'name', ''), ('foo', 'ref', '')]