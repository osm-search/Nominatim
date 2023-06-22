# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Public interface to the search code.
"""
from typing import List, Any, Optional, Iterator, Tuple
import itertools

from nominatim.api.connection import SearchConnection
from nominatim.api.types import SearchDetails
from nominatim.api.results import SearchResults, add_result_details
from nominatim.api.search.token_assignment import yield_token_assignments
from nominatim.api.search.db_search_builder import SearchBuilder, build_poi_search, wrap_near_search
from nominatim.api.search.db_searches import AbstractSearch
from nominatim.api.search.query_analyzer_factory import make_query_analyzer, AbstractQueryAnalyzer
from nominatim.api.search.query import Phrase, QueryStruct
from nominatim.api.logging import log

class ForwardGeocoder:
    """ Main class responsible for place search.
    """

    def __init__(self, conn: SearchConnection, params: SearchDetails) -> None:
        self.conn = conn
        self.params = params
        self.query_analyzer: Optional[AbstractQueryAnalyzer] = None


    @property
    def limit(self) -> int:
        """ Return the configured maximum number of search results.
        """
        return self.params.max_results


    async def build_searches(self,
                             phrases: List[Phrase]) -> Tuple[QueryStruct, List[AbstractSearch]]:
        """ Analyse the query and return the tokenized query and list of
            possible searches over it.
        """
        if self.query_analyzer is None:
            self.query_analyzer = await make_query_analyzer(self.conn)

        query = await self.query_analyzer.analyze_query(phrases)

        searches: List[AbstractSearch] = []
        if query.num_token_slots() > 0:
            # 2. Compute all possible search interpretations
            log().section('Compute abstract searches')
            search_builder = SearchBuilder(query, self.params)
            num_searches = 0
            for assignment in yield_token_assignments(query):
                searches.extend(search_builder.build(assignment))
                log().table_dump('Searches for assignment',
                                 _dump_searches(searches, query, num_searches))
                num_searches = len(searches)
            searches.sort(key=lambda s: s.penalty)

        return query, searches


    async def execute_searches(self, query: QueryStruct,
                               searches: List[AbstractSearch]) -> SearchResults:
        """ Run the abstract searches against the database until a result
            is found.
        """
        log().section('Execute database searches')
        results = SearchResults()

        num_results = 0
        min_ranking = 1000.0
        prev_penalty = 0.0
        for i, search in enumerate(searches):
            if search.penalty > prev_penalty and (search.penalty > min_ranking or i > 20):
                break
            log().table_dump(f"{i + 1}. Search", _dump_searches([search], query))
            for result in await search.lookup(self.conn, self.params):
                results.append(result)
                min_ranking = min(min_ranking, result.ranking + 0.5, search.penalty + 0.3)
            log().result_dump('Results', ((r.accuracy, r) for r in results[num_results:]))
            num_results = len(results)
            prev_penalty = search.penalty

        if results:
            min_ranking = min(r.ranking for r in results)
            results = SearchResults(r for r in results if r.ranking < min_ranking + 0.5)

        if results:
            min_rank = min(r.rank_search for r in results)

            results = SearchResults(r for r in results
                                    if r.ranking + 0.05 * (r.rank_search - min_rank)
                                       < min_ranking + 0.5)

            results.sort(key=lambda r: r.accuracy - r.calculated_importance())
            results = SearchResults(results[:self.limit])

        return results


    async def lookup_pois(self, categories: List[Tuple[str, str]],
                          phrases: List[Phrase]) -> SearchResults:
        """ Look up places by category. If phrase is given, a place search
            over the phrase will be executed first and places close to the
            results returned.
        """
        log().function('forward_lookup_pois', categories=categories, params=self.params)

        if phrases:
            query, searches = await self.build_searches(phrases)

            if query:
                searches = [wrap_near_search(categories, s) for s in searches[:50]]
                results = await self.execute_searches(query, searches)
            else:
                results = SearchResults()
        else:
            search = build_poi_search(categories, self.params.countries)
            results = await search.lookup(self.conn, self.params)

        await add_result_details(self.conn, results, self.params)
        log().result_dump('Final Results', ((r.accuracy, r) for r in results))

        return results


    async def lookup(self, phrases: List[Phrase]) -> SearchResults:
        """ Look up a single free-text query.
        """
        log().function('forward_lookup', phrases=phrases, params=self.params)
        results = SearchResults()

        if self.params.is_impossible():
            return results

        query, searches = await self.build_searches(phrases)

        if searches:
            # Execute SQL until an appropriate result is found.
            results = await self.execute_searches(query, searches[:50])
            await add_result_details(self.conn, results, self.params)
            log().result_dump('Final Results', ((r.accuracy, r) for r in results))

        return results


# pylint: disable=invalid-name,too-many-locals
def _dump_searches(searches: List[AbstractSearch], query: QueryStruct,
                   start: int = 0) -> Iterator[Optional[List[Any]]]:
    yield ['Penalty', 'Lookups', 'Housenr', 'Postcode', 'Countries', 'Qualifier', 'Rankings']

    def tk(tl: List[int]) -> str:
        tstr = [f"{query.find_lookup_word_by_id(t)}({t})" for t in tl]

        return f"[{','.join(tstr)}]"

    def fmt_ranking(f: Any) -> str:
        if not f:
            return ''
        ranks = ','.join((f"{tk(r.tokens)}^{r.penalty:.3g}" for r in f.rankings))
        if len(ranks) > 100:
            ranks = ranks[:100] + '...'
        return f"{f.column}({ranks},def={f.default:.3g})"

    def fmt_lookup(l: Any) -> str:
        if not l:
            return ''

        return f"{l.lookup_type}({l.column}{tk(l.tokens)})"


    def fmt_cstr(c: Any) -> str:
        if not c:
            return ''

        return f'{c[0]}^{c[1]}'

    for search in searches[start:]:
        fields = ('lookups', 'rankings', 'countries', 'housenumbers',
                  'postcodes', 'qualifier')
        iters = itertools.zip_longest([f"{search.penalty:.3g}"],
                                      *(getattr(search, attr, []) for attr in fields),
                                      fillvalue= '')
        for penalty, lookup, rank, cc, hnr, pc, qual in iters:
            yield [penalty, fmt_lookup(lookup), fmt_cstr(hnr),
                   fmt_cstr(pc), fmt_cstr(cc), fmt_cstr(qual), fmt_ranking(rank)]
        yield None
