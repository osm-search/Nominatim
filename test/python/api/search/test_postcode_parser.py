
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for parsing of postcodes in queries.
"""
import re
from itertools import zip_longest

import pytest

from nominatim_api.search.postcode_parser import PostcodeParser
from nominatim_api.search.query import QueryStruct, PHRASE_ANY, PHRASE_POSTCODE, PHRASE_STREET


@pytest.fixture
def pc_config(project_env):
    country_file = project_env.project_dir / 'country_settings.yaml'
    country_file.write_text(r"""
ab:
  postcode:
    pattern: "ddddd ll"
ba:
  postcode:
    pattern: "ddddd"
de:
  postcode:
    pattern: "ddddd"
gr:
  postcode:
    pattern: "(ddd) ?(dd)"
    output: \1 \2
in:
  postcode:
    pattern: "(ddd) ?(ddd)"
    output: \1\2
mc:
  postcode:
    pattern: "980dd"
mz:
  postcode:
    pattern: "(dddd)(?:-dd)?"
bn:
  postcode:
    pattern: "(ll) ?(dddd)"
    output: \1\2
ky:
  postcode:
    pattern: "(d)-(dddd)"
    output: KY\1-\2

gb:
  postcode:
    pattern: "(l?ld[A-Z0-9]?) ?(dll)"
    output: \1 \2

    """)

    return project_env


def mk_query(inp):
    query = QueryStruct([])
    phrase_split = re.split(r"([ ,:'-])", inp)

    for word, breakchar in zip_longest(*[iter(phrase_split)]*2, fillvalue='>'):
        query.add_node(breakchar, PHRASE_ANY, 0.1, word, word)

    return query


@pytest.mark.parametrize('query,pos', [('45325 Berlin', 0),
                                       ('45325:Berlin', 0),
                                       ('45325,Berlin', 0),
                                       ('Berlin 45325', 1),
                                       ('Berlin,45325', 1),
                                       ('Berlin:45325', 1),
                                       ('Hansastr,45325 Berlin', 1),
                                       ('Hansastr 45325 Berlin', 1)])
def test_simple_postcode(pc_config, query, pos):
    parser = PostcodeParser(pc_config)

    result = parser.parse(mk_query(query))

    assert result == {(pos, pos + 1, '45325'), (pos, pos + 1, '453 25')}


@pytest.mark.parametrize('query', ['EC1R 3HF', 'ec1r 3hf'])
def test_postcode_matching_case_insensitive(pc_config, query):
    parser = PostcodeParser(pc_config)

    assert parser.parse(mk_query(query)) == {(0, 2, 'EC1R 3HF')}


def test_contained_postcode(pc_config):
    parser = PostcodeParser(pc_config)

    assert parser.parse(mk_query('12345 dx')) == {(0, 1, '12345'), (0, 1, '123 45'),
                                                  (0, 2, '12345 DX')}


@pytest.mark.parametrize('query,frm,to', [('345987', 0, 1), ('345 987', 0, 2),
                                          ('Aina 345 987', 1, 3),
                                          ('Aina 23 345 987 ff', 2, 4)])
def test_postcode_with_space(pc_config, query, frm, to):
    parser = PostcodeParser(pc_config)

    result = parser.parse(mk_query(query))

    assert result == {(frm, to, '345987')}


def test_overlapping_postcode(pc_config):
    parser = PostcodeParser(pc_config)

    assert parser.parse(mk_query('123 456 78')) == {(0, 2, '123456'), (1, 3, '456 78')}


@pytest.mark.parametrize('query', ['45325-Berlin', "45325'Berlin",
                                   'Berlin-45325', "Berlin'45325", '45325Berlin'
                                   '345-987', "345'987", '345,987', '345:987'])
def test_not_a_postcode(pc_config, query):
    parser = PostcodeParser(pc_config)

    assert not parser.parse(mk_query(query))


@pytest.mark.parametrize('query', ['ba 12233', 'ba-12233'])
def test_postcode_with_country_prefix(pc_config, query):
    parser = PostcodeParser(pc_config)

    assert (0, 2, '12233') in parser.parse(mk_query(query))


def test_postcode_with_joined_country_prefix(pc_config):
    parser = PostcodeParser(pc_config)

    assert parser.parse(mk_query('ba12233')) == {(0, 1, '12233')}


def test_postcode_with_non_matching_country_prefix(pc_config):
    parser = PostcodeParser(pc_config)

    assert not parser.parse(mk_query('ky12233'))


def test_postcode_inside_postcode_phrase(pc_config):
    parser = PostcodeParser(pc_config)

    query = QueryStruct([])
    query.nodes[-1].ptype = PHRASE_STREET
    query.add_node(',', PHRASE_STREET, 0.1, '12345', '12345')
    query.add_node(',', PHRASE_POSTCODE, 0.1, 'xz', 'xz')
    query.add_node('>', PHRASE_POSTCODE, 0.1, '4444', '4444')

    assert parser.parse(query) == {(2, 3, '4444')}


def test_partial_postcode_in_postcode_phrase(pc_config):
    parser = PostcodeParser(pc_config)

    query = QueryStruct([])
    query.nodes[-1].ptype = PHRASE_POSTCODE
    query.add_node(' ', PHRASE_POSTCODE, 0.1, '2224', '2224')
    query.add_node('>', PHRASE_POSTCODE, 0.1, '12345', '12345')

    assert not parser.parse(query)
