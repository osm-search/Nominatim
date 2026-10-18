
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for parsing of postcodes in queries.
"""
import re

import pytest

from nominatim_api.search.postcode_parser import PostcodeParser
from nominatim_api.search import query as qmod


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

    """, encoding='utf-8')

    return project_env


def add_node(query, btype, ptype, word):
    query.add_node(btype, ptype,
                   qmod.PartialToken(penalty=10.0, token=-1, count=1, addr_count=1,
                                     lookup_word=word, transliterated=word))


def mk_query(inp):
    query = qmod.QueryStruct([])
    phrase_split = re.split(r"([ ,:`-])", inp)

    brk = '<'
    for word in phrase_split:
        if brk is None:
            brk = word
        else:
            add_node(query, brk, qmod.PHRASE_ANY, word)
            brk = None
    query.add_final_node()

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


def test_postcode_phrase_with_space(pc_config):
    query = qmod.QueryStruct([])
    add_node(query, '<', qmod.PHRASE_POSTCODE, 'EC1R')
    add_node(query, ' ', qmod.PHRASE_POSTCODE, '3HF')
    query.add_final_node()

    assert PostcodeParser(pc_config).parse(query) == {(0, 2, 'EC1R 3HF')}


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


@pytest.mark.parametrize('query', ['45325-Berlin', "45325`Berlin",
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

    query = qmod.QueryStruct([])
    add_node(query, '<', qmod.PHRASE_STREET, '12345')
    add_node(query, ',', qmod.PHRASE_POSTCODE, 'xz')
    add_node(query, ',', qmod.PHRASE_POSTCODE, '4444')
    add_node(query, '>', qmod.PHRASE_ANY, qmod.PARTIAL_END_TOKEN)

    assert parser.parse(query) == {(2, 3, '4444')}


def test_partial_postcode_in_postcode_phrase(pc_config):
    parser = PostcodeParser(pc_config)

    query = qmod.QueryStruct([])
    add_node(query, '<', qmod.PHRASE_POSTCODE, '2224')
    add_node(query, ' ', qmod.PHRASE_POSTCODE, '12345')
    add_node(query, '>', qmod.PHRASE_ANY, qmod.PARTIAL_END_TOKEN)

    assert not parser.parse(query)
