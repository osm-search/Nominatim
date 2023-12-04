# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Convertion from token assignment to an abstract DB search.
"""
from typing import Optional, List, Tuple, Iterator, Dict
import heapq

from nominatim.api.types import SearchDetails, DataLayer
from nominatim.api.search.query import QueryStruct, Token, TokenType, TokenRange, BreakType
from nominatim.api.search.token_assignment import TokenAssignment
import nominatim.api.search.db_search_fields as dbf
import nominatim.api.search.db_searches as dbs


def wrap_near_search(categories: List[Tuple[str, str]],
                     search: dbs.AbstractSearch) -> dbs.NearSearch:
    """ Create a new search that wraps the given search in a search
        for near places of the given category.
    """
    return dbs.NearSearch(penalty=search.penalty,
                          categories=dbf.WeightedCategories(categories,
                                                            [0.0] * len(categories)),
                          search=search)


def build_poi_search(category: List[Tuple[str, str]],
                     countries: Optional[List[str]]) -> dbs.PoiSearch:
    """ Create a new search for places by the given category, possibly
        constraint to the given countries.
    """
    if countries:
        ccs = dbf.WeightedStrings(countries, [0.0] * len(countries))
    else:
        ccs = dbf.WeightedStrings([], [])

    class _PoiData(dbf.SearchData):
        penalty = 0.0
        qualifiers = dbf.WeightedCategories(category, [0.0] * len(category))
        countries=ccs

    return dbs.PoiSearch(_PoiData())


class SearchBuilder:
    """ Build the abstract search queries from token assignments.
    """

    def __init__(self, query: QueryStruct, details: SearchDetails) -> None:
        self.query = query
        self.details = details


    @property
    def configured_for_country(self) -> bool:
        """ Return true if the search details are configured to
            allow countries in the result.
        """
        return self.details.min_rank <= 4 and self.details.max_rank >= 4 \
               and self.details.layer_enabled(DataLayer.ADDRESS)


    @property
    def configured_for_postcode(self) -> bool:
        """ Return true if the search details are configured to
            allow postcodes in the result.
        """
        return self.details.min_rank <= 5 and self.details.max_rank >= 11\
               and self.details.layer_enabled(DataLayer.ADDRESS)


    @property
    def configured_for_housenumbers(self) -> bool:
        """ Return true if the search details are configured to
            allow addresses in the result.
        """
        return self.details.max_rank >= 30 \
               and self.details.layer_enabled(DataLayer.ADDRESS)


    def build(self, assignment: TokenAssignment) -> Iterator[dbs.AbstractSearch]:
        """ Yield all possible abstract searches for the given token assignment.
        """
        sdata = self.get_search_data(assignment)
        if sdata is None:
            return

        near_items = self.get_near_items(assignment)
        if near_items is not None and not near_items:
            return # impossible compbination of near items and category parameter

        if assignment.name is None:
            if near_items and not sdata.postcodes:
                sdata.qualifiers = near_items
                near_items = None
                builder = self.build_poi_search(sdata)
            elif assignment.housenumber:
                hnr_tokens = self.query.get_tokens(assignment.housenumber,
                                                   TokenType.HOUSENUMBER)
                builder = self.build_housenumber_search(sdata, hnr_tokens, assignment.address)
            else:
                builder = self.build_special_search(sdata, assignment.address,
                                                    bool(near_items))
        else:
            builder = self.build_name_search(sdata, assignment.name, assignment.address,
                                             bool(near_items))

        if near_items:
            penalty = min(near_items.penalties)
            near_items.penalties = [p - penalty for p in near_items.penalties]
            for search in builder:
                search_penalty = search.penalty
                search.penalty = 0.0
                yield dbs.NearSearch(penalty + assignment.penalty + search_penalty,
                                     near_items, search)
        else:
            for search in builder:
                search.penalty += assignment.penalty
                yield search


    def build_poi_search(self, sdata: dbf.SearchData) -> Iterator[dbs.AbstractSearch]:
        """ Build abstract search query for a simple category search.
            This kind of search requires an additional geographic constraint.
        """
        if not sdata.housenumbers \
           and ((self.details.viewbox and self.details.bounded_viewbox) or self.details.near):
            yield dbs.PoiSearch(sdata)


    def build_special_search(self, sdata: dbf.SearchData,
                             address: List[TokenRange],
                             is_category: bool) -> Iterator[dbs.AbstractSearch]:
        """ Build abstract search queries for searches that do not involve
            a named place.
        """
        if sdata.qualifiers:
            # No special searches over qualifiers supported.
            return

        if sdata.countries and not address and not sdata.postcodes \
           and self.configured_for_country:
            yield dbs.CountrySearch(sdata)

        if sdata.postcodes and (is_category or self.configured_for_postcode):
            penalty = 0.0 if sdata.countries else 0.1
            if address:
                sdata.lookups = [dbf.FieldLookup('nameaddress_vector',
                                                 [t.token for r in address
                                                  for t in self.query.get_partials_list(r)],
                                                 'restrict')]
                penalty += 0.2
            yield dbs.PostcodeSearch(penalty, sdata)


    def build_housenumber_search(self, sdata: dbf.SearchData, hnrs: List[Token],
                                 address: List[TokenRange]) -> Iterator[dbs.AbstractSearch]:
        """ Build a simple address search for special entries where the
            housenumber is the main name token.
        """
        sdata.lookups = [dbf.FieldLookup('name_vector', [t.token for t in hnrs], 'lookup_any')]
        expected_count = sum(t.count for t in hnrs)

        partials = [t for trange in address
                       for t in self.query.get_partials_list(trange)]

        if expected_count < 8000:
            sdata.lookups.append(dbf.FieldLookup('nameaddress_vector',
                                                 [t.token for t in partials], 'restrict'))
        elif len(partials) != 1 or partials[0].count < 10000:
            sdata.lookups.append(dbf.FieldLookup('nameaddress_vector',
                                                 [t.token for t in partials], 'lookup_all'))
        else:
            sdata.lookups.append(
                dbf.FieldLookup('nameaddress_vector',
                                [t.token for t
                                 in self.query.get_tokens(address[0], TokenType.WORD)],
                                'lookup_any'))

        sdata.housenumbers = dbf.WeightedStrings([], [])
        yield dbs.PlaceSearch(0.05, sdata, expected_count)


    def build_name_search(self, sdata: dbf.SearchData,
                          name: TokenRange, address: List[TokenRange],
                          is_category: bool) -> Iterator[dbs.AbstractSearch]:
        """ Build abstract search queries for simple name or address searches.
        """
        if is_category or not sdata.housenumbers or self.configured_for_housenumbers:
            ranking = self.get_name_ranking(name)
            name_penalty = ranking.normalize_penalty()
            if ranking.rankings:
                sdata.rankings.append(ranking)
            for penalty, count, lookup in self.yield_lookups(name, address):
                sdata.lookups = lookup
                yield dbs.PlaceSearch(penalty + name_penalty, sdata, count)


    def yield_lookups(self, name: TokenRange, address: List[TokenRange])\
                          -> Iterator[Tuple[float, int, List[dbf.FieldLookup]]]:
        """ Yield all variants how the given name and address should best
            be searched for. This takes into account how frequent the terms
            are and tries to find a lookup that optimizes index use.
        """
        penalty = 0.0 # extra penalty
        name_partials = self.query.get_partials_list(name)
        name_tokens = [t.token for t in name_partials]

        addr_partials = [t for r in address for t in self.query.get_partials_list(r)]
        addr_tokens = [t.token for t in addr_partials]

        partials_indexed = all(t.is_indexed for t in name_partials) \
                           and all(t.is_indexed for t in addr_partials)
        exp_count = min(t.count for t in name_partials) / (2**(len(name_partials) - 1))

        if (len(name_partials) > 3 or exp_count < 8000) and partials_indexed:
            yield penalty, exp_count, dbf.lookup_by_names(name_tokens, addr_tokens)
            return

        # Partial term to frequent. Try looking up by rare full names first.
        name_fulls = self.query.get_tokens(name, TokenType.WORD)
        if name_fulls:
            fulls_count = sum(t.count for t in name_fulls)
            # At this point drop unindexed partials from the address.
            # This might yield wrong results, nothing we can do about that.
            if not partials_indexed:
                addr_tokens = [t.token for t in addr_partials if t.is_indexed]
                penalty += 1.2 * sum(t.penalty for t in addr_partials if not t.is_indexed)
            # Any of the full names applies with all of the partials from the address
            yield penalty, fulls_count / (2**len(addr_partials)),\
                  dbf.lookup_by_any_name([t.token for t in name_fulls], addr_tokens,
                                         'restrict' if fulls_count < 10000 else 'lookup_all')

        # To catch remaining results, lookup by name and address
        # We only do this if there is a reasonable number of results expected.
        exp_count = exp_count / (2**len(addr_partials)) if addr_partials else exp_count
        if exp_count < 10000 and all(t.is_indexed for t in name_partials):
            lookup = [dbf.FieldLookup('name_vector', name_tokens, 'lookup_all')]
            if addr_tokens:
                lookup.append(dbf.FieldLookup('nameaddress_vector', addr_tokens, 'lookup_all'))
            penalty += 0.35 * max(0, 5 - len(name_partials) - len(addr_tokens))
            yield penalty, exp_count, lookup


    def get_name_ranking(self, trange: TokenRange) -> dbf.FieldRanking:
        """ Create a ranking expression for a name term in the given range.
        """
        name_fulls = self.query.get_tokens(trange, TokenType.WORD)
        ranks = [dbf.RankedTokens(t.penalty, [t.token]) for t in name_fulls]
        ranks.sort(key=lambda r: r.penalty)
        # Fallback, sum of penalty for partials
        name_partials = self.query.get_partials_list(trange)
        default = sum(t.penalty for t in name_partials) + 0.2
        return dbf.FieldRanking('name_vector', default, ranks)


    def get_addr_ranking(self, trange: TokenRange) -> dbf.FieldRanking:
        """ Create a list of ranking expressions for an address term
            for the given ranges.
        """
        todo: List[Tuple[int, int, dbf.RankedTokens]] = []
        heapq.heappush(todo, (0, trange.start, dbf.RankedTokens(0.0, [])))
        ranks: List[dbf.RankedTokens] = []

        while todo: # pylint: disable=too-many-nested-blocks
            neglen, pos, rank = heapq.heappop(todo)
            for tlist in self.query.nodes[pos].starting:
                if tlist.ttype in (TokenType.PARTIAL, TokenType.WORD):
                    if tlist.end < trange.end:
                        chgpenalty = PENALTY_WORDCHANGE[self.query.nodes[tlist.end].btype]
                        if tlist.ttype == TokenType.PARTIAL:
                            penalty = rank.penalty + chgpenalty \
                                      + max(t.penalty for t in tlist.tokens)
                            heapq.heappush(todo, (neglen - 1, tlist.end,
                                                  dbf.RankedTokens(penalty, rank.tokens)))
                        else:
                            for t in tlist.tokens:
                                heapq.heappush(todo, (neglen - 1, tlist.end,
                                                      rank.with_token(t, chgpenalty)))
                    elif tlist.end == trange.end:
                        if tlist.ttype == TokenType.PARTIAL:
                            ranks.append(dbf.RankedTokens(rank.penalty
                                                          + max(t.penalty for t in tlist.tokens),
                                                          rank.tokens))
                        else:
                            ranks.extend(rank.with_token(t, 0.0) for t in tlist.tokens)
                        if len(ranks) >= 10:
                            # Too many variants, bail out and only add
                            # Worst-case Fallback: sum of penalty of partials
                            name_partials = self.query.get_partials_list(trange)
                            default = sum(t.penalty for t in name_partials) + 0.2
                            ranks.append(dbf.RankedTokens(rank.penalty + default, []))
                            # Bail out of outer loop
                            todo.clear()
                            break

        ranks.sort(key=lambda r: len(r.tokens))
        default = ranks[0].penalty + 0.3
        del ranks[0]
        ranks.sort(key=lambda r: r.penalty)

        return dbf.FieldRanking('nameaddress_vector', default, ranks)


    def get_search_data(self, assignment: TokenAssignment) -> Optional[dbf.SearchData]:
        """ Collect the tokens for the non-name search fields in the
            assignment.
        """
        sdata = dbf.SearchData()
        sdata.penalty = assignment.penalty
        if assignment.country:
            tokens = self.query.get_tokens(assignment.country, TokenType.COUNTRY)
            if self.details.countries:
                tokens = [t for t in tokens if t.lookup_word in self.details.countries]
                if not tokens:
                    return None
            sdata.set_strings('countries', tokens)
        elif self.details.countries:
            sdata.countries = dbf.WeightedStrings(self.details.countries,
                                                  [0.0] * len(self.details.countries))
        if assignment.housenumber:
            sdata.set_strings('housenumbers',
                              self.query.get_tokens(assignment.housenumber,
                                                    TokenType.HOUSENUMBER))
        if assignment.postcode:
            sdata.set_strings('postcodes',
                              self.query.get_tokens(assignment.postcode,
                                                    TokenType.POSTCODE))
        if assignment.qualifier:
            tokens = self.query.get_tokens(assignment.qualifier, TokenType.QUALIFIER)
            if self.details.categories:
                tokens = [t for t in tokens if t.get_category() in self.details.categories]
                if not tokens:
                    return None
            sdata.set_qualifiers(tokens)
        elif self.details.categories:
            sdata.qualifiers = dbf.WeightedCategories(self.details.categories,
                                                      [0.0] * len(self.details.categories))

        if assignment.address:
            sdata.set_ranking([self.get_addr_ranking(r) for r in assignment.address])
        else:
            sdata.rankings = []

        return sdata


    def get_near_items(self, assignment: TokenAssignment) -> Optional[dbf.WeightedCategories]:
        """ Collect tokens for near items search or use the categories
            requested per parameter.
            Returns None if no category search is requested.
        """
        if assignment.near_item:
            tokens: Dict[Tuple[str, str], float] = {}
            for t in self.query.get_tokens(assignment.near_item, TokenType.NEAR_ITEM):
                cat = t.get_category()
                # The category of a near search will be that of near_item.
                # Thus, if search is restricted to a category parameter,
                # the two sets must intersect.
                if (not self.details.categories or cat in self.details.categories)\
                   and t.penalty < tokens.get(cat, 1000.0):
                    tokens[cat] = t.penalty
            return dbf.WeightedCategories(list(tokens.keys()), list(tokens.values()))

        return None


PENALTY_WORDCHANGE = {
    BreakType.START: 0.0,
    BreakType.END: 0.0,
    BreakType.PHRASE: 0.0,
    BreakType.WORD: 0.1,
    BreakType.PART: 0.2,
    BreakType.TOKEN: 0.4
}
