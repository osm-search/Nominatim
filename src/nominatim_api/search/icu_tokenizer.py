# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of query analysis for the ICU tokenizer.
"""
from typing import Tuple, Dict, List, Optional, NamedTuple, Iterator, Any, cast
from collections import defaultdict
import dataclasses
import difflib

from icu import Transliterator

import sqlalchemy as sa

from nominatim_core.typing import SaRow
from nominatim_core.db.sqlalchemy_types import Json
from ..connection import SearchConnection
from ..logging import log
from ..search import query as qmod
from ..search.query_analyzer_factory import AbstractQueryAnalyzer


DB_TO_TOKEN_TYPE = {
    'W': qmod.TokenType.WORD,
    'w': qmod.TokenType.PARTIAL,
    'H': qmod.TokenType.HOUSENUMBER,
    'P': qmod.TokenType.POSTCODE,
    'C': qmod.TokenType.COUNTRY
}


class QueryPart(NamedTuple):
    """ Normalized and transliterated form of a single term in the query.
        When the term came out of a split during the transliteration,
        the normalized string is the full word before transliteration.
        The word number keeps track of the word before transliteration
        and can be used to identify partial transliterated terms.
    """
    token: str
    normalized: str
    word_number: int


QueryParts = List[QueryPart]
WordDict = Dict[str, List[qmod.TokenRange]]

def yield_words(terms: List[QueryPart], start: int) -> Iterator[Tuple[str, qmod.TokenRange]]:
    """ Return all combinations of words in the terms list after the
        given position.
    """
    total = len(terms)
    for first in range(start, total):
        word = terms[first].token
        yield word, qmod.TokenRange(first, first + 1)
        for last in range(first + 1, min(first + 20, total)):
            word = ' '.join((word, terms[last].token))
            yield word, qmod.TokenRange(first, last + 1)


@dataclasses.dataclass
class ICUToken(qmod.Token):
    """ Specialised token for ICU tokenizer.
    """
    word_token: str
    info: Optional[Dict[str, Any]]

    def get_category(self) -> Tuple[str, str]:
        assert self.info
        return self.info.get('class', ''), self.info.get('type', '')


    def rematch(self, norm: str) -> None:
        """ Check how well the token matches the given normalized string
            and add a penalty, if necessary.
        """
        if not self.lookup_word:
            return

        seq = difflib.SequenceMatcher(a=self.lookup_word, b=norm)
        distance = 0
        for tag, afrom, ato, bfrom, bto in seq.get_opcodes():
            if tag in ('delete', 'insert') and (afrom == 0 or ato == len(self.lookup_word)):
                distance += 1
            elif tag == 'replace':
                distance += max((ato-afrom), (bto-bfrom))
            elif tag != 'equal':
                distance += abs((ato-afrom) - (bto-bfrom))
        self.penalty += (distance/len(self.lookup_word))


    @staticmethod
    def from_db_row(row: SaRow) -> 'ICUToken':
        """ Create a ICUToken from the row of the word table.
        """
        count = 1 if row.info is None else row.info.get('count', 1)
        addr_count = 1 if row.info is None else row.info.get('addr_count', 1)

        penalty = 0.0
        if row.type == 'w':
            penalty = 0.3
        elif row.type == 'W':
            if len(row.word_token) == 1 and row.word_token == row.word:
                penalty = 0.2 if row.word.isdigit() else 0.3
        elif row.type == 'H':
            penalty = sum(0.1 for c in row.word_token if c != ' ' and not c.isdigit())
            if all(not c.isdigit() for c in row.word_token):
                penalty += 0.2 * (len(row.word_token) - 1)
        elif row.type == 'C':
            if len(row.word_token) == 1:
                penalty = 0.3

        if row.info is None:
            lookup_word = row.word
        else:
            lookup_word = row.info.get('lookup', row.word)
        if lookup_word:
            lookup_word = lookup_word.split('@', 1)[0]
        else:
            lookup_word = row.word_token

        return ICUToken(penalty=penalty, token=row.word_id, count=max(1, count),
                        lookup_word=lookup_word, is_indexed=True,
                        word_token=row.word_token, info=row.info,
                        addr_count=max(1, addr_count))



class ICUQueryAnalyzer(AbstractQueryAnalyzer):
    """ Converter for query strings into a tokenized query
        using the tokens created by a ICU tokenizer.
    """

    def __init__(self, conn: SearchConnection) -> None:
        self.conn = conn


    async def setup(self) -> None:
        """ Set up static data structures needed for the analysis.
        """
        async def _make_normalizer() -> Any:
            rules = await self.conn.get_property('tokenizer_import_normalisation')
            return Transliterator.createFromRules("normalization", rules)

        self.normalizer = await self.conn.get_cached_value('ICUTOK', 'normalizer',
                                                           _make_normalizer)

        async def _make_transliterator() -> Any:
            rules = await self.conn.get_property('tokenizer_import_transliteration')
            return Transliterator.createFromRules("transliteration", rules)

        self.transliterator = await self.conn.get_cached_value('ICUTOK', 'transliterator',
                                                               _make_transliterator)

        if 'word' not in self.conn.t.meta.tables:
            sa.Table('word', self.conn.t.meta,
                     sa.Column('word_id', sa.Integer),
                     sa.Column('word_token', sa.Text, nullable=False),
                     sa.Column('type', sa.Text, nullable=False),
                     sa.Column('word', sa.Text),
                     sa.Column('info', Json))


    async def analyze_query(self, phrases: List[qmod.Phrase]) -> qmod.QueryStruct:
        """ Analyze the given list of phrases and return the
            tokenized query.
        """
        log().section('Analyze query (using ICU tokenizer)')
        normalized = list(filter(lambda p: p.text,
                                 (qmod.Phrase(p.ptype, self.normalize_text(p.text))
                                  for p in phrases)))
        query = qmod.QueryStruct(normalized)
        log().var_dump('Normalized query', query.source)
        if not query.source:
            return query

        parts, words = self.split_query(query)
        log().var_dump('Transliterated query', lambda: _dump_transliterated(query, parts))

        for row in await self.lookup_in_db(list(words.keys())):
            for trange in words[row.word_token]:
                token = ICUToken.from_db_row(row)
                if row.type == 'S':
                    if row.info['op'] in ('in', 'near'):
                        if trange.start == 0:
                            query.add_token(trange, qmod.TokenType.NEAR_ITEM, token)
                    else:
                        if trange.start == 0 and trange.end == query.num_token_slots():
                            query.add_token(trange, qmod.TokenType.NEAR_ITEM, token)
                        else:
                            query.add_token(trange, qmod.TokenType.QUALIFIER, token)
                else:
                    query.add_token(trange, DB_TO_TOKEN_TYPE[row.type], token)

        self.add_extra_tokens(query, parts)
        self.rerank_tokens(query, parts)

        log().table_dump('Word tokens', _dump_word_tokens(query))

        return query


    def normalize_text(self, text: str) -> str:
        """ Bring the given text into a normalized form. That is the
            standardized form search will work with. All information removed
            at this stage is inevitably lost.
        """
        return cast(str, self.normalizer.transliterate(text))


    def split_query(self, query: qmod.QueryStruct) -> Tuple[QueryParts, WordDict]:
        """ Transliterate the phrases and split them into tokens.

            Returns the list of transliterated tokens together with their
            normalized form and a dictionary of words for lookup together
            with their position.
        """
        parts: QueryParts = []
        phrase_start = 0
        words = defaultdict(list)
        wordnr = 0
        for phrase in query.source:
            query.nodes[-1].ptype = phrase.ptype
            for word in phrase.text.split(' '):
                trans = self.transliterator.transliterate(word)
                if trans:
                    for term in trans.split(' '):
                        if term:
                            parts.append(QueryPart(term, word, wordnr))
                            query.add_node(qmod.BreakType.TOKEN, phrase.ptype)
                    query.nodes[-1].btype = qmod.BreakType.WORD
                wordnr += 1
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
        return await self.conn.execute(t.select().where(t.c.word_token.in_(words)))


    def add_extra_tokens(self, query: qmod.QueryStruct, parts: QueryParts) -> None:
        """ Add tokens to query that are not saved in the database.
        """
        for part, node, i in zip(parts, query.nodes, range(1000)):
            if len(part.token) <= 4 and part[0].isdigit()\
               and not node.has_tokens(i+1, qmod.TokenType.HOUSENUMBER):
                query.add_token(qmod.TokenRange(i, i+1), qmod.TokenType.HOUSENUMBER,
                                ICUToken(0.5, 0, 1, 1, part.token, True, part.token, None))


    def rerank_tokens(self, query: qmod.QueryStruct, parts: QueryParts) -> None:
        """ Add penalties to tokens that depend on presence of other token.
        """
        for i, node, tlist in query.iter_token_lists():
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
            elif tlist.ttype not in (qmod.TokenType.COUNTRY, qmod.TokenType.PARTIAL):
                norm = parts[i].normalized
                for j in range(i + 1, tlist.end):
                    if parts[j - 1].word_number != parts[j].word_number:
                        norm += '  ' + parts[j].normalized
                for token in tlist.tokens:
                    cast(ICUToken, token).rematch(norm)


def _dump_transliterated(query: qmod.QueryStruct, parts: QueryParts) -> str:
    out = query.nodes[0].btype.value
    for node, part in zip(query.nodes[1:], parts):
        out += part.token + node.btype.value
    return out


def _dump_word_tokens(query: qmod.QueryStruct) -> Iterator[List[Any]]:
    yield ['type', 'token', 'word_token', 'lookup_word', 'penalty', 'count', 'info']
    for node in query.nodes:
        for tlist in node.starting:
            for token in tlist.tokens:
                t = cast(ICUToken, token)
                yield [tlist.ttype.name, t.token, t.word_token or '',
                       t.lookup_word or '', t.penalty, t.count, t.info]


async def create_query_analyzer(conn: SearchConnection) -> AbstractQueryAnalyzer:
    """ Create and set up a new query analyzer for a database based
        on the ICU tokenizer.
    """
    out = ICUQueryAnalyzer(conn)
    await out.setup()

    return out
