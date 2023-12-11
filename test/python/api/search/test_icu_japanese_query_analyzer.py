# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for query analyzer for ICU tokenizer.
"""
from pathlib import Path

import pytest
import pytest_asyncio

from nominatim.api import NominatimAPIAsync
from nominatim.api.search.query import Phrase, PhraseType, BreakType
import nominatim.api.search.icu_tokenizer as tok

async def add_word(conn, word_id, word_token, wtype, word, info = None):
    t = conn.t.meta.tables['word']
    await conn.execute(t.insert(), {'word_id': word_id,
                                    'word_token': word_token,
                                    'type': wtype,
                                    'word': word,
                                    'info': info})


def make_phrase(query):
    return [Phrase(PhraseType.NONE, s) for s in query.split(',')]
@pytest_asyncio.fixture
async def conn(table_factory):
    """ Create an asynchronous SQLAlchemy engine for the test DB.
    """
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('tokenizer_import_normalisation', ':: lower();'),
                           ('tokenizer_import_transliteration', "'1' > '/1/'; 'ä' > 'ä '")))
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB')

    api = NominatimAPIAsync(Path('/invalid'), {})
    async with api.begin() as conn:
        yield conn
    await api.close()
@pytest.mark.asyncio
async def test_soft_phrase(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_word(conn, 100, 'da', 'w', None)
    await add_word(conn, 101, 'ban', 'w', None)
    await add_word(conn, 102, 'fu', 'w', None)
    await add_word(conn, 103, 'shi', 'w', None)

    await add_word(conn, 1, 'da ban fu', 'W', '大阪府')
    await add_word(conn, 2, 'da ban shi', 'W', '大阪市')
    await add_word(conn, 3, 'da ban', 'W', '大阪')
    query = await ana.analyze_query(make_phrase('大阪府大阪市大阪'))
    assert query.nodes[0].btype == BreakType.START
    assert query.nodes[1].btype == BreakType.SOFT_PHRASE
    assert query.nodes[2].btype == BreakType.SOFT_PHRASE
    assert query.nodes[3].btype == BreakType.END

    query2 = await ana.analyze_query(make_phrase('大阪府大阪'))
    assert query2.nodes[1].btype == BreakType.SOFT_PHRASE

    query3 = await ana.analyze_query(make_phrase('大阪市大阪'))
    assert query3.nodes[1].btype == BreakType.SOFT_PHRASE

@pytest.mark.asyncio
async def test_penalty_soft_phrase(conn):
    ana = await tok.create_query_analyzer(conn)

    await add_word(conn, 104, 'da', 'w', 'da')
    await add_word(conn, 105, 'ban', 'w', 'ban')
    await add_word(conn, 107, 'shi', 'w', 'shi')
    
    await add_word(conn, 2, 'da ban shi', 'W', '大阪市')
    await add_word(conn, 3, 'da ban', 'W', '大阪')
    await add_word(conn, 4, 'da ban shi da ban', 'W', '大阪市大阪')
    
    query = await ana.analyze_query(make_phrase('da ban shi da ban'))
    
    torder = [(tl.tokens[0].penalty, tl.tokens[0].lookup_word) for tl in query.nodes[0].starting]
    torder.sort()

    assert torder[-1][-1] == '大阪市大阪'
