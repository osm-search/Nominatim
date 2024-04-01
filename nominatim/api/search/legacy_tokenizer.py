# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of query analysis for the legacy tokenizer.
"""
from typing import Tuple, Dict, List, Optional, Iterator, Any, cast
from copy import copy
from collections import defaultdict
import dataclasses

import sqlalchemy as sa

from nominatim.typing import SaRow
from nominatim.api.connection import SearchConnection
from nominatim.api.logging import log
from nominatim.api.search import query as qmod
from nominatim.api.search.query_analyzer_factory import AbstractQueryAnalyzer

def yield_words(terms: List[str], start: int) -> Iterator[Tuple[str, qmod.TokenRange]]:
    """ Return all combinations of words in the terms list after the
        given position.
    """
    total = len(terms)
    for first in range(start, total):
        word = terms[first]
        yield word, qmod.TokenRange(first, first + 1)
        for last in range(first + 1, min(first + 20, total)):
            word = ' '.join((word, terms[last]))
            yield word, qmod.TokenRange(first, last + 1)


@dataclasses.dataclass
class LegacyToken(qmod.Token):
    """ Specialised token for legacy tokenizer.
    """
    word_token: str
    category: Optional[Tuple[str, str]]
    country: Optional[str]
    operator: Optional[str]

    @property
    def info(self) -> Dict[str, Any]:
        """ Dictionary of additional properties of the token.
            Should only be used for debugging purposes.
        """
        return {'category': self.category,
                'country': self.country,
                'operator': self.operator}


    def get_category(self) -> Tuple[str, str]:
        assert self.category
        return self.category


class LegacyQueryAnalyzer(AbstractQueryAnalyzer):
    """ Converter for query strings into a tokenized query
        using the tokens created by a legacy tokenizer.
    """

    def __init__(self, conn: SearchConnection) -> None:
        self.conn = conn

    async def setup(self) -> None:
        """ Set up static data structures needed for the analysis.
        """
        self.max_word_freq = int(await self.conn.get_property('tokenizer_maxwordfreq'))
        if 'word' not in self.conn.t.meta.tables:
            sa.Table('word', self.conn.t.meta,
                     sa.Column('word_id', sa.Integer),
                     sa.Column('word_token', sa.Text, nullable=False),
                     sa.Column('word', sa.Text),
                     sa.Column('class', sa.Text),
                     sa.Column('type', sa.Text),
                     sa.Column('country_code', sa.Text),
                     sa.Column('search_name_count', sa.Integer),
                     sa.Column('operator', sa.Text))


    async def analyze_query(self, phrases: List[qmod.Phrase]) -> qmod.QueryStruct:
        """ Analyze the given list of phrases and return the
            tokenized query.
        """
        log().section('Analyze query (using Legacy tokenizer)')

        normalized = []
        if phrases:
            for row in await self.conn.execute(sa.select(*(sa.func.make_standard_name(p.text)
                                                           for p in phrases))):
                normalized = [qmod.Phrase(p.ptype, r) for r, p in zip(row, phrases) if r]
                break

        query = qmod.QueryStruct(normalized)
        log().var_dump('Normalized query', query.source)
        if not query.source:
            return query

        parts, words = self.split_query(query)
        lookup_words = list(words.keys())
        log().var_dump('Split query', parts)
        log().var_dump('Extracted words', lookup_words)

        for row in await self.lookup_in_db(lookup_words):
            for trange in words[row.word_token.strip()]:
                token, ttype = self.make_token(row)
                if ttype == qmod.TokenType.NEAR_ITEM:
                    if trange.start == 0:
                        query.add_token(trange, qmod.TokenType.NEAR_ITEM, token)
                elif ttype == qmod.TokenType.QUALIFIER:
                    query.add_token(trange, qmod.TokenType.QUALIFIER, token)
                    if trange.start == 0 or trange.end == query.num_token_slots():
                        token = copy(token)
                        token.penalty += 0.1 * (query.num_token_slots())
                        query.add_token(trange, qmod.TokenType.NEAR_ITEM, token)
                elif ttype != qmod.TokenType.PARTIAL or trange.start + 1 == trange.end:
                    query.add_token(trange, ttype, token)

        self.add_extra_tokens(query, parts)
        self.rerank_tokens(query)

        log().table_dump('Word tokens', _dump_word_tokens(query))

        return query


    def normalize_text(self, text: str) -> str:
        """ Bring the given text into a normalized form.

            This only removes case, so some difference with the normalization
            in the phrase remains.
        """
        return text.lower()


    def split_query(self, query: qmod.QueryStruct) -> Tuple[List[str],
                                                            Dict[str, List[qmod.TokenRange]]]:
        """ Transliterate the phrases and split them into tokens.

            Returns a list of transliterated tokens and a dictionary
            of words for lookup together with their position.
        """
        parts: List[str] = []
        phrase_start = 0
        words = defaultdict(list)
        for phrase in query.source:
            query.nodes[-1].ptype = phrase.ptype
            for trans in phrase.text.split(' '):
                if trans:
                    for term in trans.split(' '):
                        if term:
                            parts.append(trans)
                            query.add_node(qmod.BreakType.TOKEN, phrase.ptype)
                    query.nodes[-1].btype = qmod.BreakType.WORD
            query.nodes[-1].btype = qmod.BreakType.PHRASE
            for word, wrange in yield_words(parts, phrase_start):
                words[word].append(wrange)
            phrase_start = len(parts)
        query.nodes[-1].btype = qmod.BreakType.END

        return parts, words


    async def lookup_in_db(self, words: List[str]) -> 'sa.Result[Any]':
        """ Return the token information from the database for the
            given word tokens.
        """
        t = self.conn.t.meta.tables['word']

        sql = t.select().where(t.c.word_token.in_(words + [' ' + w for w in words]))

        return await self.conn.execute(sql)


    def make_token(self, row: SaRow) -> Tuple[LegacyToken, qmod.TokenType]:
        """ Create a LegacyToken from the row of the word table.
            Also determines the type of token.
        """
        penalty = 0.0
        is_indexed = True

        rowclass = getattr(row, 'class')

        if row.country_code is not None:
            ttype = qmod.TokenType.COUNTRY
            lookup_word = row.country_code
        elif rowclass is not None:
            if rowclass == 'place' and  row.type == 'house':
                ttype = qmod.TokenType.HOUSENUMBER
                lookup_word = row.word_token[1:]
            elif rowclass == 'place' and  row.type == 'postcode':
                ttype = qmod.TokenType.POSTCODE
                lookup_word = row.word_token[1:]
            else:
                ttype = qmod.TokenType.NEAR_ITEM if row.operator in ('in', 'near')\
                        else qmod.TokenType.QUALIFIER
                lookup_word = row.word
        elif row.word_token.startswith(' '):
            ttype = qmod.TokenType.WORD
            lookup_word = row.word or row.word_token[1:]
        else:
            ttype = qmod.TokenType.PARTIAL
            lookup_word = row.word_token
            penalty = 0.21
            if row.search_name_count > self.max_word_freq:
                is_indexed = False

        return LegacyToken(penalty=penalty, token=row.word_id,
                           count=max(1, row.search_name_count or 1),
                           addr_count=1, # not supported
                           lookup_word=lookup_word,
                           word_token=row.word_token.strip(),
                           category=(rowclass, row.type) if rowclass is not None else None,
                           country=row.country_code,
                           operator=row.operator,
                           is_indexed=is_indexed),\
               ttype


    def add_extra_tokens(self, query: qmod.QueryStruct, parts: List[str]) -> None:
        """ Add tokens to query that are not saved in the database.
        """
        for part, node, i in zip(parts, query.nodes, range(1000)):
            if len(part) <= 4 and part.isdigit()\
               and not node.has_tokens(i+1, qmod.TokenType.HOUSENUMBER):
                query.add_token(qmod.TokenRange(i, i+1), qmod.TokenType.HOUSENUMBER,
                                LegacyToken(penalty=0.5, token=0, count=1, addr_count=1,
                                            lookup_word=part, word_token=part,
                                            category=None, country=None,
                                            operator=None, is_indexed=True))


    def rerank_tokens(self, query: qmod.QueryStruct) -> None:
        """ Add penalties to tokens that depend on presence of other token.
        """
        for _, node, tlist in query.iter_token_lists():
            if tlist.ttype == qmod.TokenType.POSTCODE:
                for repl in node.starting:
                    if repl.end == tlist.end and repl.ttype != qmod.TokenType.POSTCODE \
                       and (repl.ttype != qmod.TokenType.HOUSENUMBER
                            or len(tlist.tokens[0].lookup_word) > 4):
                        repl.add_penalty(0.39)
            elif tlist.ttype == qmod.TokenType.HOUSENUMBER \
                 and len(tlist.tokens[0].lookup_word) <= 3:
                if any(c.isdigit() for c in tlist.tokens[0].lookup_word):
                    for repl in node.starting:
                        if repl.end == tlist.end and repl.ttype != qmod.TokenType.HOUSENUMBER:
                            repl.add_penalty(0.5 - tlist.tokens[0].penalty)



def _dump_word_tokens(query: qmod.QueryStruct) -> Iterator[List[Any]]:
    yield ['type', 'token', 'word_token', 'lookup_word', 'penalty', 'count', 'info']
    for node in query.nodes:
        for tlist in node.starting:
            for token in tlist.tokens:
                t = cast(LegacyToken, token)
                yield [tlist.ttype.name, t.token, t.word_token or '',
                       t.lookup_word or '', t.penalty, t.count, t.info]


async def create_query_analyzer(conn: SearchConnection) -> AbstractQueryAnalyzer:
    """ Create and set up a new query analyzer for a database based
        on the ICU tokenizer.
    """
    out = LegacyQueryAnalyzer(conn)
    await out.setup()

    return out
