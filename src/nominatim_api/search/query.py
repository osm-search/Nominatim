# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Datastructures for a tokenized query.
"""
from typing import Dict, List, Tuple, Optional, Iterator
from abc import ABC, abstractmethod
from collections import defaultdict
import dataclasses


BreakType = str
""" Type of break between tokens.
"""
BREAK_START = '<'
""" Begin of the query. """
BREAK_END = '>'
""" End of the query. """
BREAK_PHRASE = ','
""" Hard break between two phrases. Address parts cannot cross hard
    phrase boundaries."""
BREAK_SOFT_PHRASE = ':'
""" Likely break between two phrases. Address parts should not cross soft
    phrase boundaries. Soft breaks can be inserted by a preprocessor
    that is analysing the input string.
"""
BREAK_WORD = ' '
""" Break between words. """
BREAK_PART = '-'
""" Break inside a word, for example a hyphen or apostrophe. """
BREAK_TOKEN = '`'
""" Break created as a result of tokenization.
    This may happen in languages without spaces between words.
"""


TokenType = str
""" Type of token.
"""
TOKEN_WORD = 'W'
""" Full name of a place. """
TOKEN_PARTIAL = 'w'
""" Word term without breaks, does not necessarily represent a full name. """
TOKEN_HOUSENUMBER = 'H'
""" Housenumber term. """
TOKEN_POSTCODE = 'P'
""" Postal code term. """
TOKEN_COUNTRY = 'C'
""" Country name or reference. """
TOKEN_QUALIFIER = 'Q'
""" Special term used together with name (e.g. _Hotel_ Bellevue). """
TOKEN_NEAR_ITEM = 'N'
""" Special term used as searchable object(e.g. supermarket in ...). """


PhraseType = int
""" Designation of a phrase.
"""
PHRASE_ANY = 0
""" No specific designation (i.e. source is free-form query). """
PHRASE_AMENITY = 1
""" Contains name or type of a POI. """
PHRASE_STREET = 2
""" Contains a street name optionally with a housenumber. """
PHRASE_CITY = 3
""" Contains the postal city. """
PHRASE_COUNTY = 4
""" Contains the equivalent of a county. """
PHRASE_STATE = 5
""" Contains a state or province. """
PHRASE_POSTCODE = 6
""" Contains a postal code. """
PHRASE_COUNTRY = 7
""" Contains the country name or code. """


def _phrase_compatible_with(ptype: PhraseType, ttype: TokenType,
                            is_full_phrase: bool) -> bool:
    """ Check if the given token type can be used with the phrase type.
    """
    if ptype == PHRASE_ANY:
        return not is_full_phrase or ttype != TOKEN_QUALIFIER
    if ptype == PHRASE_AMENITY:
        return ttype in (TOKEN_WORD, TOKEN_PARTIAL)\
               or (is_full_phrase and ttype == TOKEN_NEAR_ITEM)\
               or (not is_full_phrase and ttype == TOKEN_QUALIFIER)
    if ptype == PHRASE_STREET:
        return ttype in (TOKEN_WORD, TOKEN_PARTIAL, TOKEN_HOUSENUMBER)
    if ptype == PHRASE_POSTCODE:
        return ttype == TOKEN_POSTCODE
    if ptype == PHRASE_COUNTRY:
        return ttype == TOKEN_COUNTRY

    return ttype in (TOKEN_WORD, TOKEN_PARTIAL)


@dataclasses.dataclass
class Token(ABC):
    """ Base type for tokens.
        Specific query analyzers must implement the concrete token class.
    """

    penalty: float
    token: int
    count: int
    addr_count: int
    lookup_word: str

    @abstractmethod
    def get_category(self) -> Tuple[str, str]:
        """ Return the category restriction for qualifier terms and
            category objects.
        """


@dataclasses.dataclass
class TokenRange:
    """ Indexes of query nodes over which a token spans.
    """
    start: int
    end: int
    penalty: Optional[float] = None

    def __lt__(self, other: 'TokenRange') -> bool:
        return self.end <= other.start

    def __le__(self, other: 'TokenRange') -> bool:
        return NotImplemented

    def __gt__(self, other: 'TokenRange') -> bool:
        return self.start >= other.end

    def __ge__(self, other: 'TokenRange') -> bool:
        return NotImplemented

    def replace_start(self, new_start: int) -> 'TokenRange':
        """ Return a new token range with the new start.
        """
        return TokenRange(new_start, self.end)

    def replace_end(self, new_end: int) -> 'TokenRange':
        """ Return a new token range with the new end.
        """
        return TokenRange(self.start, new_end)

    def split(self, index: int) -> Tuple['TokenRange', 'TokenRange']:
        """ Split the span into two spans at the given index.
            The index must be within the span.
        """
        return self.replace_end(index), self.replace_start(index)


@dataclasses.dataclass
class TokenList:
    """ List of all tokens of a given type going from one breakpoint to another.
    """
    end: int
    ttype: TokenType
    tokens: List[Token]

    def add_penalty(self, penalty: float) -> None:
        """ Add the given penalty to all tokens in the list.
        """
        for token in self.tokens:
            token.penalty += penalty


@dataclasses.dataclass
class QueryNode:
    """ A node of the query representing a break between terms.

        The node also contains information on the source term
        ending at the node. The tokens are created from this information.
    """
    btype: BreakType
    ptype: PhraseType

    penalty: float
    """ Penalty for the break at this node.
    """
    term_lookup: str
    """ Transliterated term following this node.
    """
    term_normalized: str
    """ Normalised form of term following this node.
        When the token resulted from a split during transliteration,
        then this string contains the complete source term.
    """

    starting: List[TokenList] = dataclasses.field(default_factory=list)
    """ List of all full tokens starting at this node.
    """
    partial: Optional[Token] = None
    """ Base token going to the next node.
        May be None when the query has parts for which no words are known.
        Note that the query may still be parsable when there are other
        types of tokens spanning over the gap.
    """

    def adjust_break(self, btype: BreakType, penalty: float) -> None:
        """ Change the break type and penalty for this node.
        """
        self.btype = btype
        self.penalty = penalty

    def has_tokens(self, end: int, *ttypes: TokenType) -> bool:
        """ Check if there are tokens of the given types ending at the
            given node.
        """
        return any(tl.end == end and tl.ttype in ttypes for tl in self.starting)

    def get_tokens(self, end: int, ttype: TokenType) -> Optional[List[Token]]:
        """ Get the list of tokens of the given type starting at this node
            and ending at the node 'end'. Returns 'None' if no such
            tokens exist.
        """
        for tlist in self.starting:
            if tlist.end == end and tlist.ttype == ttype:
                return tlist.tokens
        return None


@dataclasses.dataclass
class Phrase:
    """ A normalized query part. Phrases may be typed which means that
        they then represent a specific part of the address.
    """
    ptype: PhraseType
    text: str


class QueryStruct:
    """ A tokenized search query together with the normalized source
        from which the tokens have been parsed.

        The query contains a list of nodes that represent the breaks
        between words. Tokens span between nodes, which don't necessarily
        need to be direct neighbours. Thus the query is represented as a
        directed acyclic graph.

        When created, a query contains a single node: the start of the
        query. Further nodes can be added by appending to 'nodes'.
    """

    def __init__(self, source: List[Phrase]) -> None:
        self.source = source
        self.nodes: List[QueryNode] = \
            [QueryNode(BREAK_START, source[0].ptype if source else PHRASE_ANY,
                       0.0, '', '')]

    def num_token_slots(self) -> int:
        """ Return the length of the query in vertice steps.
        """
        return len(self.nodes) - 1

    def add_node(self, btype: BreakType, ptype: PhraseType,
                 break_penalty: float = 0.0,
                 term_lookup: str = '', term_normalized: str = '') -> None:
        """ Append a new break node with the given break type.
            The phrase type denotes the type for any tokens starting
            at the node.
        """
        self.nodes.append(QueryNode(btype, ptype, break_penalty, term_lookup, term_normalized))

    def add_token(self, trange: TokenRange, ttype: TokenType, token: Token) -> None:
        """ Add a token to the query. 'start' and 'end' are the indexes of the
            nodes from which to which the token spans. The indexes must exist
            and are expected to be in the same phrase.
            'ttype' denotes the type of the token and 'token' the token to
            be inserted.

            If the token type is not compatible with the phrase it should
            be added to, then the token is silently dropped.
        """
        snode = self.nodes[trange.start]
        if ttype == TOKEN_PARTIAL:
            assert snode.partial is None
            if _phrase_compatible_with(snode.ptype, TOKEN_PARTIAL, False):
                snode.partial = token
        else:
            full_phrase = snode.btype in (BREAK_START, BREAK_PHRASE)\
                and self.nodes[trange.end].btype in (BREAK_PHRASE, BREAK_END)
            if _phrase_compatible_with(snode.ptype, ttype, full_phrase):
                tlist = snode.get_tokens(trange.end, ttype)
                if tlist is None:
                    snode.starting.append(TokenList(trange.end, ttype, [token]))
                else:
                    tlist.append(token)

    def get_tokens(self, trange: TokenRange, ttype: TokenType) -> List[Token]:
        """ Get the list of tokens of a given type, spanning the given
            nodes. The nodes must exist. If no tokens exist, an
            empty list is returned.

            Cannot be used to get the partial token.
        """
        assert ttype != TOKEN_PARTIAL
        return self.nodes[trange.start].get_tokens(trange.end, ttype) or []

    def iter_partials(self, trange: TokenRange) -> Iterator[Token]:
        """ Iterate over the partial tokens between the given nodes.
            Missing partials are ignored.
        """
        return (n.partial for n in self.nodes[trange.start:trange.end] if n.partial is not None)

    def iter_token_lists(self) -> Iterator[Tuple[int, QueryNode, TokenList]]:
        """ Iterator over all token lists except partial tokens in the query.
        """
        for i, node in enumerate(self.nodes):
            for tlist in node.starting:
                yield i, node, tlist

    def find_lookup_word_by_id(self, token: int) -> str:
        """ Find the first token with the given token ID and return
            its lookup word. Returns 'None' if no such token exists.
            The function is very slow and must only be used for
            debugging.
        """
        for node in self.nodes:
            if node.partial is not None and node.partial.token == token:
                return f"[P]{node.partial.lookup_word}"
            for tlist in node.starting:
                for t in tlist.tokens:
                    if t.token == token:
                        return f"[{tlist.ttype}]{t.lookup_word}"
        return 'None'

    def get_transliterated_query(self) -> str:
        """ Return a string representation of the transliterated query
            with the character representation of the different break types.

            For debugging purposes only.
        """
        return ''.join(''.join((n.term_lookup, n.btype)) for n in self.nodes)

    def extract_words(self, base_penalty: float = 0.0,
                      start: int = 0,
                      endpos: Optional[int] = None) -> Dict[str, List[TokenRange]]:
        """ Add all combinations of words that can be formed from the terms
            between the given start and endnode. The terms are joined with
            spaces for each break. Words can never go across a BREAK_PHRASE.

            The functions returns a dictionary of possible words with their
            position within the query and a penalty. The penalty is computed
            from the base_penalty plus the penalty for each node the word
            crosses.
        """
        if endpos is None:
            endpos = len(self.nodes)

        words: Dict[str, List[TokenRange]] = defaultdict(list)

        for first in range(start, endpos - 1):
            word = self.nodes[first + 1].term_lookup
            penalty = base_penalty
            words[word].append(TokenRange(first, first + 1, penalty=penalty))
            if self.nodes[first + 1].btype != BREAK_PHRASE:
                for last in range(first + 2, min(first + 20, endpos)):
                    word = ' '.join((word, self.nodes[last].term_lookup))
                    penalty += self.nodes[last - 1].penalty
                    words[word].append(TokenRange(first, last, penalty=penalty))
                    if self.nodes[last].btype == BREAK_PHRASE:
                        break

        return words
