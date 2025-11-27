# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Data structures for more complex fields in abstract search descriptions.
"""
from typing import List, Tuple, Iterator, Dict, Type, cast
import dataclasses

import sqlalchemy as sa

from ..typing import SaFromClause, SaColumn, SaExpression
from ..utils.json_writer import JsonWriter
from .query import Token
from . import db_search_lookups as lookups


class CountedTokenIDs:
    """ A list of token IDs with their respective counts, sorted
        from least frequent to most frequent.

        If a token count is one, then statistics are likely to be unavaible
        and a relatively high count is assumed instead.
    """

    def __init__(self, tokens: Iterator[Token], count_column: str = 'count'):
        self.tokens = list({(cast(int, getattr(t, count_column)), t.token) for t in tokens})
        self.tokens.sort(key=lambda t: t[0] if t[0] > 1 else 100000)

    def __len__(self) -> int:
        return len(self.tokens)

    def get_num_lookup_tokens(self, limit: int, fac: int) -> int:
        """ Suggest the number of tokens to be used for an index lookup.
            The idea here is to use as few items as possible while making
            sure the number of rows returned stays below 'limit' which
            makes recheck of the returned rows more expensive than adding
            another item for the index lookup. 'fac' is the factor by which
            the limit is increased every time a lookup item is added.

            If the list of tokens doesn't seem suitable at all for index
            lookup, -1 is returned.
        """
        length = len(self.tokens)
        min_count = self.tokens[0][0]
        if min_count == 1:
            return min(length, 3)  # no statistics available, use index

        for i in range(min(length, 3)):
            if min_count < limit:
                return i + 1
            limit = limit * fac

        return -1

    def min_count(self) -> int:
        return self.tokens[0][0]

    def expected_for_all_search(self, fac: int = 5) -> int:
        return int(self.tokens[0][0] / (fac**(len(self.tokens) - 1)))

    def get_tokens(self) -> List[int]:
        return [t[1] for t in self.tokens]

    def get_head_tokens(self, num_tokens: int) -> List[int]:
        return [t[1] for t in self.tokens[:num_tokens]]

    def get_tail_tokens(self, first: int) -> List[int]:
        return [t[1] for t in self.tokens[first:]]

    def split_lookup(self, split: int, column: str) -> 'List[FieldLookup]':
        lookup = [FieldLookup(column, self.get_head_tokens(split), lookups.LookupAll)]
        if split < len(self.tokens):
            lookup.append(FieldLookup(column, self.get_tail_tokens(split), lookups.Restrict))
        return lookup


@dataclasses.dataclass
class WeightedStrings:
    """ A list of strings together with a penalty.
    """
    values: List[str]
    penalties: List[float]

    def __bool__(self) -> bool:
        return bool(self.values)

    def __iter__(self) -> Iterator[Tuple[str, float]]:
        return iter(zip(self.values, self.penalties))

    def get_penalty(self, value: str, default: float = 1000.0) -> float:
        """ Get the penalty for the given value. Returns the given default
            if the value does not exist.
        """
        try:
            return self.penalties[self.values.index(value)]
        except ValueError:
            pass
        return default


@dataclasses.dataclass
class WeightedCategories:
    """ A list of class/type tuples together with a penalty.
    """
    values: List[Tuple[str, str]]
    penalties: List[float]

    def __bool__(self) -> bool:
        return bool(self.values)

    def __iter__(self) -> Iterator[Tuple[Tuple[str, str], float]]:
        return iter(zip(self.values, self.penalties))

    def get_penalty(self, value: Tuple[str, str], default: float = 1000.0) -> float:
        """ Get the penalty for the given value. Returns the given default
            if the value does not exist.
        """
        try:
            return self.penalties[self.values.index(value)]
        except ValueError:
            pass
        return default

    def sql_restrict(self, table: SaFromClause) -> SaExpression:
        """ Return an SQLAlcheny expression that restricts the
            class and type columns of the given table to the values
            in the list.
            Must not be used with an empty list.
        """
        assert self.values
        if len(self.values) == 1:
            return sa.and_(table.c.class_ == self.values[0][0],
                           table.c.type == self.values[0][1])

        return sa.or_(*(sa.and_(table.c.class_ == c, table.c.type == t)
                        for c, t in self.values))


@dataclasses.dataclass(order=True)
class RankedTokens:
    """ List of tokens together with the penalty of using it.
    """
    penalty: float
    tokens: List[int]

    def with_token(self, t: Token, transition_penalty: float) -> 'RankedTokens':
        """ Create a new RankedTokens list with the given token appended.
            The tokens penalty as well as the given transition penalty
            are added to the overall penalty.
        """
        return RankedTokens(self.penalty + t.penalty + transition_penalty,
                            self.tokens + [t.token])


@dataclasses.dataclass
class FieldRanking:
    """ A list of rankings to be applied sequentially until one matches.
        The matched ranking determines the penalty. If none matches a
        default penalty is applied.
    """
    column: str
    default: float
    rankings: List[RankedTokens]

    def normalize_penalty(self) -> float:
        """ Reduce the default and ranking penalties, such that the minimum
            penalty is 0. Return the penalty that was subtracted.
        """
        if self.rankings:
            min_penalty = min(self.default, min(r.penalty for r in self.rankings))
        else:
            min_penalty = self.default
        if min_penalty > 0.0:
            self.default -= min_penalty
            for ranking in self.rankings:
                ranking.penalty -= min_penalty
        return min_penalty

    def sql_penalty(self, table: SaFromClause) -> SaColumn:
        """ Create an SQL expression for the rankings.
        """
        assert self.rankings

        rout = JsonWriter().start_array()
        for rank in self.rankings:
            rout.start_array().value(rank.penalty).next()
            rout.start_array()
            for token in rank.tokens:
                rout.value(token).next()
            rout.end_array()
            rout.end_array().next()
        rout.end_array()

        return sa.func.weigh_search(table.c[self.column], rout(), self.default)


@dataclasses.dataclass
class FieldLookup:
    """ A list of tokens to be searched for. The column names the database
        column to search in and the lookup_type the operator that is applied.
        'lookup_all' requires all tokens to match. 'lookup_any' requires
        one of the tokens to match. 'restrict' requires to match all tokens
        but avoids the use of indexes.
    """
    column: str
    tokens: List[int]
    lookup_type: Type[lookups.LookupType]

    def sql_condition(self, table: SaFromClause) -> SaColumn:
        """ Create an SQL expression for the given match condition.
        """
        return self.lookup_type(table, self.column, self.tokens)


class SearchData:
    """ Search fields derived from query and token assignment
        to be used with the SQL queries.
    """
    penalty: float

    lookups: List[FieldLookup] = []
    rankings: List[FieldRanking]

    housenumbers: WeightedStrings = WeightedStrings([], [])
    postcodes: WeightedStrings = WeightedStrings([], [])
    countries: WeightedStrings = WeightedStrings([], [])

    qualifiers: WeightedCategories = WeightedCategories([], [])

    def set_strings(self, field: str, tokens: List[Token]) -> None:
        """ Set on of the WeightedStrings properties from the given
            token list. Adapt the global penalty, so that the
            minimum penalty is 0.
        """
        if tokens:
            min_penalty = min(t.penalty for t in tokens)
            self.penalty += min_penalty
            wstrs = WeightedStrings([t.lookup_word for t in tokens],
                                    [t.penalty - min_penalty for t in tokens])

            setattr(self, field, wstrs)

    def set_countries(self, tokens: List[Token]) -> None:
        """ Set the WeightedStrings properties for countries. Multiple
            entries for the same country are deduplicated and the minimum
            penalty is used. Adapts the global penalty, so that the
            minimum penalty is 0.
        """
        if tokens:
            min_penalty = min(t.penalty for t in tokens)
            self.penalty += min_penalty
            countries: dict[str, float] = {}
            for t in tokens:
                cc = t.get_country()
                countries[cc] = min(t.penalty - min_penalty, countries.get(cc, 10000))
            self.countries = WeightedStrings(list(countries.keys()), list(countries.values()))

    def set_qualifiers(self, tokens: List[Token]) -> None:
        """ Set the qulaifier field from the given tokens.
        """
        if tokens:
            categories: Dict[Tuple[str, str], float] = {}
            min_penalty = 1000.0
            for t in tokens:
                min_penalty = min(min_penalty, t.penalty)
                cat = t.get_category()
                if t.penalty < categories.get(cat, 1000.0):
                    categories[cat] = t.penalty
            self.penalty += min_penalty
            self.qualifiers = WeightedCategories(list(categories.keys()),
                                                 list(categories.values()))

    def set_ranking(self, rankings: List[FieldRanking]) -> None:
        """ Set the list of rankings and normalize the ranking.
        """
        self.rankings = []
        for ranking in rankings:
            if ranking.rankings:
                self.penalty += ranking.normalize_penalty()
                self.rankings.append(ranking)
            else:
                self.penalty += ranking.default


def lookup_by_any_name(name_tokens: List[int], addr_restrict_tokens: List[int],
                       addr_lookup_tokens: List[int]) -> List[FieldLookup]:
    """ Create a lookup list where name tokens are looked up via index
        and only one of the name tokens must be present.
        Potential address tokens are used to restrict the search further.
    """
    lookup = [FieldLookup('name_vector', name_tokens, lookups.LookupAny)]
    if addr_restrict_tokens:
        lookup.append(FieldLookup('nameaddress_vector', addr_restrict_tokens, lookups.Restrict))
    if addr_lookup_tokens:
        lookup.append(FieldLookup('nameaddress_vector', addr_lookup_tokens, lookups.LookupAll))

    return lookup
