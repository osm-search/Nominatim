# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the sanitizer that enables language-dependent analyzers.
"""
import pytest

from nominatim.data.place_info import PlaceInfo
from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.data.country_info import setup_country_config

class TestWithDefaults:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config


    def run_sanitizer_on(self, country, **kwargs):
        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                           'country_code': country})
        name, _ = PlaceSanitizer([{'step': 'tag-analyzer-by-language'}],
                                 self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix, p.attr) for p in name])


    def test_no_names(self):
        assert self.run_sanitizer_on('de') == []


    def test_simple(self):
        res = self.run_sanitizer_on('fr', name='Foo',name_de='Zoo', ref_abc='M')

        assert res == [('Foo', 'name', None, {}),
                       ('M', 'ref', 'abc', {'analyzer': 'abc'}),
                       ('Zoo', 'name', 'de', {'analyzer': 'de'})]


    @pytest.mark.parametrize('suffix', ['DE', 'asbc'])
    def test_illegal_suffix(self, suffix):
        assert self.run_sanitizer_on('fr', **{'name_' + suffix: 'Foo'}) \
                 == [('Foo', 'name', suffix, {})]


class TestFilterKind:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config


    def run_sanitizer_on(self, filt, **kwargs):
        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                           'country_code': 'de'})
        name, _ = PlaceSanitizer([{'step': 'tag-analyzer-by-language',
                                   'filter-kind': filt}],
                                 self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix, p.attr) for p in name])


    def test_single_exact_name(self):
        res = self.run_sanitizer_on(['name'], name_fr='A', ref_fr='12',
                                              shortname_fr='C', name='D')

        assert res == [('12', 'ref',  'fr', {}),
                       ('A',  'name', 'fr', {'analyzer': 'fr'}),
                       ('C',  'shortname', 'fr', {}),
                       ('D',  'name', None, {})]


    def test_single_pattern(self):
        res = self.run_sanitizer_on(['.*name'],
                                    name_fr='A', ref_fr='12', namexx_fr='B',
                                    shortname_fr='C', name='D')

        assert res == [('12', 'ref',  'fr', {}),
                       ('A',  'name', 'fr', {'analyzer': 'fr'}),
                       ('B',  'namexx', 'fr', {}),
                       ('C',  'shortname', 'fr', {'analyzer': 'fr'}),
                       ('D',  'name', None, {})]


    def test_multiple_patterns(self):
        res = self.run_sanitizer_on(['.*name', 'ref'],
                                    name_fr='A', ref_fr='12', oldref_fr='X',
                                    namexx_fr='B', shortname_fr='C', name='D')

        assert res == [('12', 'ref',  'fr', {'analyzer': 'fr'}),
                       ('A',  'name', 'fr', {'analyzer': 'fr'}),
                       ('B',  'namexx', 'fr', {}),
                       ('C',  'shortname', 'fr', {'analyzer': 'fr'}),
                       ('D',  'name', None, {}),
                       ('X',  'oldref', 'fr', {})]


class TestDefaultCountry:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        setup_country_config(def_config)
        self.config = def_config


    def run_sanitizer_append(self, mode,  country, **kwargs):
        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                           'country_code': country})
        name, _ = PlaceSanitizer([{'step': 'tag-analyzer-by-language',
                                   'use-defaults': mode,
                                   'mode': 'append'}],
                                 self.config).process_names(place)

        assert all(isinstance(p.attr, dict) for p in name)
        assert all(len(p.attr) <= 1 for p in name)
        assert all(not p.attr or ('analyzer' in p.attr and p.attr['analyzer'])
                   for p in name)

        return sorted([(p.name, p.attr.get('analyzer', '')) for p in name])


    def run_sanitizer_replace(self, mode,  country, **kwargs):
        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                           'country_code': country})
        name, _ = PlaceSanitizer([{'step': 'tag-analyzer-by-language',
                                   'use-defaults': mode,
                                   'mode': 'replace'}],
                                 self.config).process_names(place)

        assert all(isinstance(p.attr, dict) for p in name)
        assert all(len(p.attr) <= 1 for p in name)
        assert all(not p.attr or ('analyzer' in p.attr and p.attr['analyzer'])
                   for p in name)

        return sorted([(p.name, p.attr.get('analyzer', '')) for p in name])


    def test_missing_country(self):
        place = PlaceInfo({'name': {'name': 'something'}})
        name, _ = PlaceSanitizer([{'step': 'tag-analyzer-by-language',
                                   'use-defaults': 'all',
                                   'mode': 'replace'}],
                                 self.config).process_names(place)

        assert len(name) == 1
        assert name[0].name == 'something'
        assert name[0].suffix is None
        assert 'analyzer' not in name[0].attr


    def test_mono_unknown_country(self):
        expect = [('XX', '')]

        assert self.run_sanitizer_replace('mono', 'xx', name='XX') == expect
        assert self.run_sanitizer_append('mono', 'xx', name='XX') == expect


    def test_mono_monoling_replace(self):
        res = self.run_sanitizer_replace('mono', 'de', name='Foo')

        assert res == [('Foo', 'de')]


    def test_mono_monoling_append(self):
        res = self.run_sanitizer_append('mono', 'de', name='Foo')

        assert res == [('Foo', ''), ('Foo', 'de')]


    def test_mono_multiling(self):
        expect = [('XX', '')]

        assert self.run_sanitizer_replace('mono', 'ch', name='XX') == expect
        assert self.run_sanitizer_append('mono', 'ch', name='XX') == expect


    def test_all_unknown_country(self):
        expect = [('XX', '')]

        assert self.run_sanitizer_replace('all', 'xx', name='XX') == expect
        assert self.run_sanitizer_append('all', 'xx', name='XX') == expect


    def test_all_monoling_replace(self):
        res = self.run_sanitizer_replace('all', 'de', name='Foo')

        assert res == [('Foo', 'de')]


    def test_all_monoling_append(self):
        res = self.run_sanitizer_append('all', 'de', name='Foo')

        assert res == [('Foo', ''), ('Foo', 'de')]


    def test_all_multiling_append(self):
        res = self.run_sanitizer_append('all', 'ch', name='XX')

        assert res == [('XX', ''),
                       ('XX', 'de'), ('XX', 'fr'), ('XX', 'it'), ('XX', 'rm')]


    def test_all_multiling_replace(self):
        res = self.run_sanitizer_replace('all', 'ch', name='XX')

        assert res == [('XX', 'de'), ('XX', 'fr'), ('XX', 'it'), ('XX', 'rm')]


class TestCountryWithWhitelist:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config


    def run_sanitizer_on(self, mode,  country, **kwargs):
        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()},
                           'country_code': country})
        name, _ = PlaceSanitizer([{'step': 'tag-analyzer-by-language',
                                   'use-defaults': mode,
                                   'mode': 'replace',
                                   'whitelist': ['de', 'fr', 'ru']}],
                                 self.config).process_names(place)

        assert all(isinstance(p.attr, dict) for p in name)
        assert all(len(p.attr) <= 1 for p in name)
        assert all(not p.attr or ('analyzer' in p.attr and p.attr['analyzer'])
                   for p in name)

        return sorted([(p.name, p.attr.get('analyzer', '')) for p in name])


    def test_mono_monoling(self):
        assert self.run_sanitizer_on('mono', 'de', name='Foo') == [('Foo', 'de')]
        assert self.run_sanitizer_on('mono', 'pt', name='Foo') == [('Foo', '')]


    def test_mono_multiling(self):
        assert self.run_sanitizer_on('mono', 'ca', name='Foo') == [('Foo', '')]


    def test_all_monoling(self):
        assert self.run_sanitizer_on('all', 'de', name='Foo') == [('Foo', 'de')]
        assert self.run_sanitizer_on('all', 'pt', name='Foo') == [('Foo', '')]


    def test_all_multiling(self):
        assert self.run_sanitizer_on('all', 'ca', name='Foo') == [('Foo', 'fr')]
        assert self.run_sanitizer_on('all', 'ch', name='Foo') \
            == [('Foo', 'de'), ('Foo', 'fr')]


class TestWhiteList:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config


    def run_sanitizer_on(self, whitelist, **kwargs):
        place = PlaceInfo({'name': {k.replace('_', ':'): v for k, v in kwargs.items()}})
        name, _ = PlaceSanitizer([{'step': 'tag-analyzer-by-language',
                                   'mode': 'replace',
                                   'whitelist': whitelist}],
                                 self.config).process_names(place)

        assert all(isinstance(p.attr, dict) for p in name)
        assert all(len(p.attr) <= 1 for p in name)
        assert all(not p.attr or ('analyzer' in p.attr and p.attr['analyzer'])
                   for p in name)

        return sorted([(p.name, p.attr.get('analyzer', '')) for p in name])


    def test_in_whitelist(self):
        assert self.run_sanitizer_on(['de', 'xx'], ref_xx='123') == [('123', 'xx')]


    def test_not_in_whitelist(self):
        assert self.run_sanitizer_on(['de', 'xx'], ref_yy='123') == [('123', '')]


    def test_empty_whitelist(self):
        assert self.run_sanitizer_on([], ref_yy='123') == [('123', '')]
