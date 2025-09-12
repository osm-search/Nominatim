# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of query analysis for the ICU tokenizer.
"""
from typing import Tuple, Dict, List, Optional, Iterator, Any, cast
import dataclasses
import difflib
import re
from itertools import zip_longest

from icu import Transliterator

import sqlalchemy as sa

from ..errors import UsageError
from ..typing import SaRow
from ..sql.sqlalchemy_types import Json
from ..connection import SearchConnection
from ..logging import log
from . import query as qmod
from ..query_preprocessing.config import QueryConfig
from ..query_preprocessing.base import QueryProcessingFunc
from .query_analyzer_factory import AbstractQueryAnalyzer
from .postcode_parser import PostcodeParser


DB_TO_TOKEN_TYPE = {
    'W': qmod.TOKEN_WORD,
    'w': qmod.TOKEN_PARTIAL,
    'H': qmod.TOKEN_HOUSENUMBER,
    'P': qmod.TOKEN_POSTCODE,
    'C': qmod.TOKEN_COUNTRY
}

PENALTY_BREAK = {
     qmod.BREAK_START: -0.5,
     qmod.BREAK_END: -0.5,
     qmod.BREAK_PHRASE: -0.5,
     qmod.BREAK_SOFT_PHRASE: -0.5,
     qmod.BREAK_WORD: 0.1,
     qmod.BREAK_PART: 0.2,
     qmod.BREAK_TOKEN: 0.4
}


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
            penalty += 0.3
        elif row.type == 'W':
            if len(row.word_token) == 1 and row.word_token == row.word:
                penalty += 0.2 if row.word.isdigit() else 0.3
        elif row.type == 'H':
            penalty += sum(0.1 for c in row.word_token if c != ' ' and not c.isdigit())
            if all(not c.isdigit() for c in row.word_token):
                penalty += 0.2 * (len(row.word_token) - 1)
        elif row.type == 'C':
            if len(row.word_token) == 1:
                penalty += 0.3

        if row.info is None:
            lookup_word = row.word
        else:
            lookup_word = row.info.get('lookup', row.word)
        if lookup_word:
            lookup_word = lookup_word.split('@', 1)[0]
        else:
            lookup_word = row.word_token

        return ICUToken(penalty=penalty, token=row.word_id, count=max(1, count),
                        lookup_word=lookup_word,
                        word_token=row.word_token, info=row.info,
                        addr_count=max(1, addr_count))


@dataclasses.dataclass
class ICUAnalyzerConfig:
    postcode_parser: PostcodeParser
    normalizer: Transliterator
    transliterator: Transliterator
    preprocessors: List[QueryProcessingFunc]

    @staticmethod
    async def create(conn: SearchConnection) -> 'ICUAnalyzerConfig':
        rules = await conn.get_property('tokenizer_import_normalisation')
        normalizer = Transliterator.createFromRules("normalization", rules)

        rules = await conn.get_property('tokenizer_import_transliteration')
        transliterator = Transliterator.createFromRules("transliteration", rules)

        preprocessing_rules = conn.config.load_sub_configuration('icu_tokenizer.yaml',
                                                                 config='TOKENIZER_CONFIG')\
                                         .get('query-preprocessing', [])

        preprocessors: List[QueryProcessingFunc] = []
        for func in preprocessing_rules:
            if 'step' not in func:
                raise UsageError("Preprocessing rule is missing the 'step' attribute.")
            if not isinstance(func['step'], str):
                raise UsageError("'step' attribute must be a simple string.")

            module = conn.config.load_plugin_module(
                        func['step'], 'nominatim_api.query_preprocessing')
            preprocessors.append(
                module.create(QueryConfig(func).set_normalizer(normalizer)))

        return ICUAnalyzerConfig(PostcodeParser(conn.config),
                                 normalizer, transliterator, preprocessors)


class ICUQueryAnalyzer(AbstractQueryAnalyzer):
    """ Converter for query strings into a tokenized query
        using the tokens created by a ICU tokenizer.
    """
    def __init__(self, conn: SearchConnection, config: ICUAnalyzerConfig) -> None:
        self.conn = conn
        self.postcode_parser = config.postcode_parser
        self.normalizer = config.normalizer
        self.transliterator = config.transliterator
        self.preprocessors = config.preprocessors

    async def analyze_query(self, phrases: List[qmod.Phrase]) -> qmod.QueryStruct:
        """ Analyze the given list of phrases and return the
            tokenized query.
        """
        log().section('Analyze query (using ICU tokenizer)')
        for func in self.preprocessors:
            phrases = func(phrases)
        query = qmod.QueryStruct(phrases)

        log().var_dump('Normalized query', query.source)
        if not query.source:
            return query

        self.split_query(query)
        log().var_dump('Transliterated query',
                       lambda: ''.join(f"{n.term_lookup}{n.btype}" for n in query.nodes)
                               + ' / '
                               + ''.join(f"{n.term_normalized}{n.btype}" for n in query.nodes))
        words = query.extract_words()

        for row in await self.lookup_in_db(list(words.keys())):
            for trange in words[row.word_token]:
                # Create a new token for each position because the token
                # penalty can vary depending on the position in the query.
                # (See rerank_tokens() below.)
                token = ICUToken.from_db_row(row)
                if row.type == 'S':
                    if row.info['op'] in ('in', 'near'):
                        if trange.start == 0:
                            query.add_token(trange, qmod.TOKEN_NEAR_ITEM, token)
                    else:
                        if trange.start == 0 and trange.end == query.num_token_slots():
                            query.add_token(trange, qmod.TOKEN_NEAR_ITEM, token)
                        else:
                            query.add_token(trange, qmod.TOKEN_QUALIFIER, token)
                else:
                    query.add_token(trange, DB_TO_TOKEN_TYPE[row.type], token)

        self.add_extra_tokens(query)
        for start, end, pc in self.postcode_parser.parse(query):
            term = ' '.join(n.term_lookup for n in query.nodes[start + 1:end + 1])
            query.add_token(qmod.TokenRange(start, end),
                            qmod.TOKEN_POSTCODE,
                            ICUToken(penalty=0.0, token=0, count=1, addr_count=1,
                                     lookup_word=pc, word_token=term,
                                     info=None))
        self.rerank_tokens(query)
        self.compute_break_penalties(query)

        log().table_dump('Word tokens', _dump_word_tokens(query))

        return query

    def normalize_text(self, text: str) -> str:
        """ Bring the given text into a normalized form. That is the
            standardized form search will work with. All information removed
            at this stage is inevitably lost.
        """
        return cast(str, self.normalizer.transliterate(text)).strip('-: ')

    def split_transliteration(self, trans: str, word: str) -> list[tuple[str, str]]:
        """ Split the given transliteration string into sub-words and
            return them together with the original part of the word.
        """
        subwords = trans.split(' ')

        if len(subwords) == 1:
            return [(trans, word)]

        tlist = []
        titer = filter(None, subwords)
        current_trans: Optional[str] = next(titer)
        assert current_trans
        current_word = ''
        for letter in word:
            current_word += letter
            if self.transliterator.transliterate(current_word).rstrip() == current_trans:
                tlist.append((current_trans, current_word))
                current_trans = next(titer, None)
                if current_trans is None:
                    return tlist
                current_word = ''

        if current_word:
            tlist.append((current_trans, current_word))

        return tlist

    def split_query(self, query: qmod.QueryStruct) -> None:
        """ Transliterate the phrases and split them into tokens.
        """
        for phrase in query.source:
            query.nodes[-1].ptype = phrase.ptype
            phrase_split = re.split('([ :-])', phrase.text)
            # The zip construct will give us the pairs of word/break from
            # the regular expression split. As the split array ends on the
            # final word, we simply use the fillvalue to even out the list and
            # add the phrase break at the end.
            for word, breakchar in zip_longest(*[iter(phrase_split)]*2, fillvalue=','):
                if not word:
                    continue
                if trans := self.transliterator.transliterate(word):
                    for term, term_word in self.split_transliteration(trans, word):
                        if term:
                            query.add_node(qmod.BREAK_TOKEN, phrase.ptype, term, term_word)
                    query.nodes[-1].btype = breakchar

        query.nodes[-1].btype = qmod.BREAK_END

    async def lookup_in_db(self, words: List[str]) -> 'sa.Result[Any]':
        """ Return the token information from the database for the
            given word tokens.

            This function excludes postcode tokens
        """
        t = self.conn.t.meta.tables['word']
        return await self.conn.execute(t.select()
                                        .where(t.c.word_token.in_(words))
                                        .where(t.c.type != 'P'))

    def add_extra_tokens(self, query: qmod.QueryStruct) -> None:
        """ Add tokens to query that are not saved in the database.
        """
        need_hnr = False
        for i, node in enumerate(query.nodes):
            is_full_token = node.btype not in (qmod.BREAK_TOKEN, qmod.BREAK_PART)
            if need_hnr and is_full_token \
                    and len(node.term_normalized) <= 4 and node.term_normalized.isdigit():
                query.add_token(qmod.TokenRange(i-1, i), qmod.TOKEN_HOUSENUMBER,
                                ICUToken(penalty=0.5, token=0,
                                         count=1, addr_count=1,
                                         lookup_word=node.term_lookup,
                                         word_token=node.term_lookup, info=None))

            need_hnr = is_full_token and not node.has_tokens(i+1, qmod.TOKEN_HOUSENUMBER)

    def rerank_tokens(self, query: qmod.QueryStruct) -> None:
        """ Add penalties to tokens that depend on presence of other token.
        """
        for start, end, tlist in query.iter_tokens_by_edge():
            if len(tlist) > 1:
                # If it looks like a Postcode, give preference.
                if qmod.TOKEN_POSTCODE in tlist:
                    for ttype, tokens in tlist.items():
                        if ttype != qmod.TOKEN_POSTCODE and \
                               (ttype != qmod.TOKEN_HOUSENUMBER or
                                start + 1 > end or
                                len(query.nodes[end].term_lookup) > 4):
                            for token in tokens:
                                token.penalty += 0.39
                        if (start + 1 == end):
                            if partial := query.nodes[start].partial:
                                partial.penalty += 0.39

                # If it looks like a simple housenumber, prefer that.
                if qmod.TOKEN_HOUSENUMBER in tlist:
                    hnr_lookup = tlist[qmod.TOKEN_HOUSENUMBER][0].lookup_word
                    if len(hnr_lookup) <= 3 and any(c.isdigit() for c in hnr_lookup):
                        penalty = 0.5 - tlist[qmod.TOKEN_HOUSENUMBER][0].penalty
                        for ttype, tokens in tlist.items():
                            if ttype != qmod.TOKEN_HOUSENUMBER:
                                for token in tokens:
                                    token.penalty += penalty
                        if (start + 1 == end):
                            if partial := query.nodes[start].partial:
                                partial.penalty += penalty

            # rerank tokens against the normalized form
            norm = ''.join(f"{n.term_normalized}{'' if n.btype == qmod.BREAK_TOKEN else ' '}"
                           for n in query.nodes[start + 1:end + 1]).strip()
            for ttype, tokens in tlist.items():
                if ttype != qmod.TOKEN_COUNTRY:
                    for token in tokens:
                        cast(ICUToken, token).rematch(norm)

    def compute_break_penalties(self, query: qmod.QueryStruct) -> None:
        """ Set the break penalties for the nodes in the query.
        """
        for node in query.nodes:
            node.penalty = PENALTY_BREAK[node.btype]


def _dump_word_tokens(query: qmod.QueryStruct) -> Iterator[List[Any]]:
    yield ['type', 'from', 'to', 'token', 'word_token', 'lookup_word', 'penalty', 'count', 'info']
    for i, node in enumerate(query.nodes):
        if node.partial is not None:
            t = cast(ICUToken, node.partial)
            yield [qmod.TOKEN_PARTIAL, str(i), str(i + 1), t.token,
                   t.word_token, t.lookup_word, t.penalty, t.count, t.info]
        for tlist in node.starting:
            for token in tlist.tokens:
                t = cast(ICUToken, token)
                yield [tlist.ttype, str(i), str(tlist.end), t.token, t.word_token or '',
                       t.lookup_word or '', t.penalty, t.count, t.info]


async def create_query_analyzer(conn: SearchConnection) -> AbstractQueryAnalyzer:
    """ Create and set up a new query analyzer for a database based
        on the ICU tokenizer.
    """
    async def _get_config() -> ICUAnalyzerConfig:
        if 'word' not in conn.t.meta.tables:
            sa.Table('word', conn.t.meta,
                     sa.Column('word_id', sa.Integer),
                     sa.Column('word_token', sa.Text, nullable=False),
                     sa.Column('type', sa.Text, nullable=False),
                     sa.Column('word', sa.Text),
                     sa.Column('info', Json))

        return await ICUAnalyzerConfig.create(conn)

    config = await conn.get_cached_value('ICUTOK', 'config', _get_config)

    return ICUQueryAnalyzer(conn, config)
