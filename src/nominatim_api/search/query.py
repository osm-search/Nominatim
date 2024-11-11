# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Datastructures for a tokenized query.
"""
from typing import List, Tuple, Optional, Iterator
from abc import ABC, abstractmethod
import dataclasses
import enum


class BreakType(enum.Enum):
    """ Type of break between tokens.
    """
    START = '<'
    """ Begin of the query. """
    END = '>'
    """ End of the query. """
    PHRASE = ','
    """ Break between two phrases. """
    WORD = ' '
    """ Break between words. """
    PART = '-'
    """ Break inside a word, for example a hyphen or apostrophe. """
    TOKEN = '`'
    """ Break created as a result of tokenization.
        This may happen in languages without spaces between words.
    """


class TokenType(enum.Enum):
    """ Type of token.
    """
    WORD = enum.auto()
    """ Full name of a place. """
    PARTIAL = enum.auto()
    """ Word term without breaks, does not necessarily represent a full name. """
    HOUSENUMBER = enum.auto()
    """ Housenumber term. """
    POSTCODE = enum.auto()
    """ Postal code term. """
    COUNTRY = enum.auto()
    """ Country name or reference. """
    QUALIFIER = enum.auto()
    """ Special term used together with name (e.g. _Hotel_ Bellevue). """
    NEAR_ITEM = enum.auto()
    """ Special term used as searchable object(e.g. supermarket in ...). """


class PhraseType(enum.Enum):
    """ Designation of a phrase.
    """
    NONE = 0
    """ No specific designation (i.e. source is free-form query). """
    AMENITY = enum.auto()
    """ Contains name or type of a POI. """
    STREET = enum.auto()
    """ Contains a street name optionally with a housenumber. """
    CITY = enum.auto()
    """ Contains the postal city. """
    COUNTY = enum.auto()
    """ Contains the equivalent of a county. """
    STATE = enum.auto()
    """ Contains a state or province. """
    POSTCODE = enum.auto()
    """ Contains a postal code. """
    COUNTRY = enum.auto()
    """ Contains the country name or code. """

    def compatible_with(self, ttype: TokenType,
                        is_full_phrase: bool) -> bool:
        """ Check if the given token type can be used with the phrase type.
        """
        if self == PhraseType.NONE:
            return not is_full_phrase or ttype != TokenType.QUALIFIER
        if self == PhraseType.AMENITY:
            return ttype in (TokenType.WORD, TokenType.PARTIAL)\
                   or (is_full_phrase and ttype == TokenType.NEAR_ITEM)\
                   or (not is_full_phrase and ttype == TokenType.QUALIFIER)
        if self == PhraseType.STREET:
            return ttype in (TokenType.WORD, TokenType.PARTIAL, TokenType.HOUSENUMBER)
        if self == PhraseType.POSTCODE:
            return ttype == TokenType.POSTCODE
        if self == PhraseType.COUNTRY:
            return ttype == TokenType.COUNTRY

        return ttype in (TokenType.WORD, TokenType.PARTIAL)


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
    """
    btype: BreakType
    ptype: PhraseType
    starting: List[TokenList] = dataclasses.field(default_factory=list)

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
            [QueryNode(BreakType.START, source[0].ptype if source else PhraseType.NONE)]

    def num_token_slots(self) -> int:
        """ Return the length of the query in vertice steps.
        """
        return len(self.nodes) - 1

    def add_node(self, btype: BreakType, ptype: PhraseType) -> None:
        """ Append a new break node with the given break type.
            The phrase type denotes the type for any tokens starting
            at the node.
        """
        self.nodes.append(QueryNode(btype, ptype))

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
        full_phrase = snode.btype in (BreakType.START, BreakType.PHRASE)\
            and self.nodes[trange.end].btype in (BreakType.PHRASE, BreakType.END)
        if snode.ptype.compatible_with(ttype, full_phrase):
            tlist = snode.get_tokens(trange.end, ttype)
            if tlist is None:
                snode.starting.append(TokenList(trange.end, ttype, [token]))
            else:
                tlist.append(token)

    def get_tokens(self, trange: TokenRange, ttype: TokenType) -> List[Token]:
        """ Get the list of tokens of a given type, spanning the given
            nodes. The nodes must exist. If no tokens exist, an
            empty list is returned.
        """
        return self.nodes[trange.start].get_tokens(trange.end, ttype) or []

    def get_partials_list(self, trange: TokenRange) -> List[Token]:
        """ Create a list of partial tokens between the given nodes.
            The list is composed of the first token of type PARTIAL
            going to the subsequent node. Such PARTIAL tokens are
            assumed to exist.
        """
        return [next(iter(self.get_tokens(TokenRange(i, i+1), TokenType.PARTIAL)))
                for i in range(trange.start, trange.end)]

    def iter_token_lists(self) -> Iterator[Tuple[int, QueryNode, TokenList]]:
        """ Iterator over all token lists in the query.
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
            for tlist in node.starting:
                for t in tlist.tokens:
                    if t.token == token:
                        return f"[{tlist.ttype.name[0]}]{t.lookup_word}"
        return 'None'
