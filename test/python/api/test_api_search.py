# SPDX-FileCopyrightText: 2023 Nominatim developer community <https://nominatim.org>
#
# SPDX-License-Identifier: GPL-3.0-or-later

# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for search API calls.

These tests make sure that all Python code is correct and executable.
Functional tests can be found in the BDD test suite.
"""
import json

import pytest

import sqlalchemy as sa

import nominatim.api as napi
import nominatim.api.logging as loglib

@pytest.fixture(autouse=True)
def setup_icu_tokenizer(apiobj):
    """ Setup the propoerties needed for using the ICU tokenizer.
    """
    apiobj.add_data('properties',
                    [{'property': 'tokenizer', 'value': 'icu'},
                     {'property': 'tokenizer_import_normalisation', 'value': ':: lower();'},
                     {'property': 'tokenizer_import_transliteration', 'value': "'1' > '/1/'; 'ä' > 'ä '"},
                    ])


def test_search_no_content(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB')

    assert apiobj.api.search('foo') == []


def test_search_simple_word(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB',
                  content=[(55, 'test', 'W', 'test', None),
                           (2, 'test', 'w', 'test', None)])

    apiobj.add_placex(place_id=444, class_='place', type='village',
                      centroid=(1.3, 0.7))
    apiobj.add_search_name(444, names=[2, 55])

    results = apiobj.api.search('TEST')

    assert [r.place_id for r in results] == [444]


@pytest.mark.parametrize('logtype', ['text', 'html'])
def test_search_with_debug(apiobj, table_factory, logtype):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB',
                  content=[(55, 'test', 'W', 'test', None),
                           (2, 'test', 'w', 'test', None)])

    apiobj.add_placex(place_id=444, class_='place', type='village',
                      centroid=(1.3, 0.7))
    apiobj.add_search_name(444, names=[2, 55])

    loglib.set_log_output(logtype)
    results = apiobj.api.search('TEST')

    assert loglib.get_and_disable()


def test_address_no_content(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB')

    assert apiobj.api.search_address(amenity='hotel',
                                     street='Main St 34',
                                     city='Happyville',
                                     county='Wideland',
                                     state='Praerie',
                                     postalcode='55648',
                                     country='xx') == []


@pytest.mark.parametrize('atype,address,search', [('street', 26, 26),
                                                  ('city', 16, 18),
                                                  ('county', 12, 12),
                                                  ('state', 8, 8)])
def test_address_simple_places(apiobj, table_factory, atype, address, search):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB',
                  content=[(55, 'test', 'W', 'test', None),
                           (2, 'test', 'w', 'test', None)])

    apiobj.add_placex(place_id=444,
                      rank_address=address, rank_search=search,
                      centroid=(1.3, 0.7))
    apiobj.add_search_name(444, names=[2, 55], address_rank=address, search_rank=search)

    results = apiobj.api.search_address(**{atype: 'TEST'})

    assert [r.place_id for r in results] == [444]


def test_address_country(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB',
                  content=[(None, 'ro', 'C', 'ro', None)])
    apiobj.add_country('ro', 'POLYGON((0 0, 0 1, 1 1, 1 0, 0 0))')
    apiobj.add_country_name('ro', {'name': 'România'})

    assert len(apiobj.api.search_address(country='ro')) == 1


def test_category_no_categories(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB')

    assert apiobj.api.search_category([], near_query='Berlin') == []


def test_category_no_content(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB')

    assert apiobj.api.search_category([('amenity', 'restaurant')]) == []


def test_category_simple_restaurant(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB')

    apiobj.add_placex(place_id=444, class_='amenity', type='restaurant',
                      centroid=(1.3, 0.7))
    apiobj.add_search_name(444, names=[2, 55], address_rank=16, search_rank=18)

    results = apiobj.api.search_category([('amenity', 'restaurant')],
                                         near=(1.3, 0.701), near_radius=0.015)

    assert [r.place_id for r in results] == [444]


def test_category_with_search_phrase(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB',
                  content=[(55, 'test', 'W', 'test', None),
                           (2, 'test', 'w', 'test', None)])

    apiobj.add_placex(place_id=444, class_='place', type='village',
                      rank_address=16, rank_search=18,
                      centroid=(1.3, 0.7))
    apiobj.add_search_name(444, names=[2, 55], address_rank=16, search_rank=18)
    apiobj.add_placex(place_id=95, class_='amenity', type='restaurant',
                      centroid=(1.3, 0.7003))

    results = apiobj.api.search_category([('amenity', 'restaurant')],
                                         near_query='TEST')

    assert [r.place_id for r in results] == [95]
