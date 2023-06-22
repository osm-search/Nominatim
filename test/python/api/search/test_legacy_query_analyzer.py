# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for query analyzer for legacy tokenizer.
"""
from pathlib import Path

import pytest
import pytest_asyncio

from nominatim.api import NominatimAPIAsync
from nominatim.api.search.query import Phrase, PhraseType, TokenType, BreakType
import nominatim.api.search.legacy_tokenizer as tok
from nominatim.api.logging import set_log_output, get_and_disable


async def add_word(conn, word_id, word_token, word, count):
    t = conn.t.meta.tables['word']
    await conn.execute(t.insert(), {'word_id': word_id,
                                    'word_token': word_token,
                                    'search_name_count': count,
                                    'word': word})


async def add_housenumber(conn, word_id, hnr):
    t = conn.t.meta.tables['word']
    await conn.execute(t.insert(), {'word_id': word_id,
                                    'word_token': ' ' + hnr,
                                    'word': hnr,
                                    'class': 'place',
                                    'type': 'house'})


async def add_postcode(conn, word_id, postcode):
    t = conn.t.meta.tables['word']
    await conn.execute(t.insert(), {'word_id': word_id,
                                    'word_token': ' ' + postcode,
                                    'word': postcode,
                                    'class': 'place',
                                    'type': 'postcode'})


async def add_special_term(conn, word_id, word_token, cls, typ, op):
    t = conn.t.meta.tables['word']
    await conn.execute(t.insert(), {'word_id': word_id,
                                    'word_token': word_token,
                                    'word': word_token,
                                    'class': cls,
                                    'type': typ,
                                    'operator': op})


def make_phrase(query):
    return [Phrase(PhraseType.NONE, s) for s in query.split(',')]


@pytest_asyncio.fixture
async def conn(table_factory, temp_db_cursor):
    """ Create an asynchronous SQLAlchemy engine for the test DB.
    """
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('tokenizer_maxwordfreq', '10000'), ))
    table_factory('word',
                  definition="""word_id INT, word_token TEXT, word TEXT,
                                class TEXT, type TEXT, country_code TEXT,
                                search_name_count INT, operator TEXT
                             """)

    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION make_standard_name(name TEXT)
                              RETURNS TEXT AS $$ SELECT lower(name); $$ LANGUAGE SQL;""")

    api = NominatimAPIAsync(Path('/invalid'), {})
    async with api.begin() as conn:
        yield conn
    await api.close()


@pytest.mark.asyncio
async def test_empty_phrase(conn):
    ana = await tok.create_query_analyzer(conn)

    query = await ana.analyze_query([])

    assert len(query.source) == 0
    assert query.num_token_slots() == 0


@pytest.mark.asyncio
async def test_single_phrase_with_unknown_terms(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_word(conn, 1, 'foo', 'FOO', 3)

    query = await ana.analyze_query(make_phrase('foo BAR'))

    assert len(query.source) == 1
    assert query.source[0].ptype == PhraseType.NONE
    assert query.source[0].text == 'foo bar'

    assert query.num_token_slots() == 2
    assert len(query.nodes[0].starting) == 1
    assert not query.nodes[1].starting


@pytest.mark.asyncio
async def test_multiple_phrases(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_word(conn, 1, 'one', 'one', 13)
    await add_word(conn, 2, 'two', 'two', 45)
    await add_word(conn, 100, 'one two', 'one two', 3)
    await add_word(conn, 3, 'three', 'three', 4584)

    query = await ana.analyze_query(make_phrase('one two,three'))

    assert len(query.source) == 2


@pytest.mark.asyncio
async def test_housenumber_token(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_housenumber(conn, 556, '45 a')

    query = await ana.analyze_query(make_phrase('45 A'))

    assert query.num_token_slots() == 2
    assert len(query.nodes[0].starting) == 2

    query.nodes[0].starting.sort(key=lambda tl: tl.end)

    hn1 = query.nodes[0].starting[0]
    assert hn1.ttype == TokenType.HOUSENUMBER
    assert hn1.end == 1
    assert hn1.tokens[0].token == 0

    hn2 = query.nodes[0].starting[1]
    assert hn2.ttype == TokenType.HOUSENUMBER
    assert hn2.end == 2
    assert hn2.tokens[0].token == 556


@pytest.mark.asyncio
async def test_postcode_token(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_postcode(conn, 34, '45ax')

    query = await ana.analyze_query(make_phrase('45AX'))

    assert query.num_token_slots() == 1
    assert [tl.ttype for tl in query.nodes[0].starting] == [TokenType.POSTCODE]


@pytest.mark.asyncio
async def test_partial_tokens(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_word(conn, 1, ' foo', 'foo', 99)
    await add_word(conn, 1, 'foo', 'FOO', 99)
    await add_word(conn, 1, 'bar', 'FOO', 990000)

    query = await ana.analyze_query(make_phrase('foo bar'))

    assert query.num_token_slots() == 2

    first = query.nodes[0].starting
    first.sort(key=lambda tl: tl.tokens[0].penalty)
    assert [tl.ttype for tl in first] == [TokenType.WORD, TokenType.PARTIAL]
    assert all(tl.tokens[0].lookup_word == 'foo' for tl in first)

    second = query.nodes[1].starting
    assert [tl.ttype for tl in second] == [TokenType.PARTIAL]
    assert not second[0].tokens[0].is_indexed


@pytest.mark.asyncio
@pytest.mark.parametrize('term,order', [('23456', ['POSTCODE', 'HOUSENUMBER', 'WORD', 'PARTIAL']),
                                        ('3', ['HOUSENUMBER', 'POSTCODE', 'WORD', 'PARTIAL'])
                                       ])
async def test_penalty_postcodes_and_housenumbers(conn, term, order):
    ana = await tok.create_query_analyzer(conn)

    await add_postcode(conn, 1, term)
    await add_housenumber(conn, 2, term)
    await add_word(conn, 3, term, term, 5)
    await add_word(conn, 4, ' ' + term, term, 1)

    query = await ana.analyze_query(make_phrase(term))

    assert query.num_token_slots() == 1

    torder = [(tl.tokens[0].penalty, tl.ttype.name) for tl in query.nodes[0].starting]
    torder.sort()

    assert [t[1] for t in torder] == order


@pytest.mark.asyncio
async def test_category_words_only_at_beginning(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_special_term(conn, 1, 'foo', 'amenity', 'restaurant', 'in')
    await add_word(conn, 2, ' bar', 'BAR', 1)

    query = await ana.analyze_query(make_phrase('foo BAR foo'))

    assert query.num_token_slots() == 3
    assert len(query.nodes[0].starting) == 1
    assert query.nodes[0].starting[0].ttype == TokenType.CATEGORY
    assert not query.nodes[2].starting


@pytest.mark.asyncio
async def test_qualifier_words(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_special_term(conn, 1, 'foo', 'amenity', 'restaurant', '-')
    await add_word(conn, 2, ' bar', 'w', None)

    query = await ana.analyze_query(make_phrase('foo BAR foo BAR foo'))

    assert query.num_token_slots() == 5
    assert set(t.ttype for t in query.nodes[0].starting) == {TokenType.CATEGORY, TokenType.QUALIFIER}
    assert set(t.ttype for t in query.nodes[2].starting) == {TokenType.QUALIFIER}
    assert set(t.ttype for t in query.nodes[4].starting) == {TokenType.CATEGORY, TokenType.QUALIFIER}


@pytest.mark.asyncio
@pytest.mark.parametrize('logtype', ['text', 'html'])
async def test_log_output(conn, logtype):
    ana = await tok.create_query_analyzer(conn)

    await add_word(conn, 1, 'foo', 'FOO', 99)

    set_log_output(logtype)
    await ana.analyze_query(make_phrase('foo'))

    assert get_and_disable()
