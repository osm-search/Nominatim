# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Public interface to the search code.
"""
from typing import List, Any, Optional, Iterator, Tuple, Dict
import itertools
import re
import datetime as dt
import difflib

from ..connection import SearchConnection
from ..types import SearchDetails
from ..results import SearchResult, SearchResults, add_result_details
from ..logging import log
from .token_assignment import yield_token_assignments
from .db_search_builder import SearchBuilder, build_poi_search, wrap_near_search
from .db_searches import AbstractSearch
from .query_analyzer_factory import make_query_analyzer, AbstractQueryAnalyzer
from .query import Phrase, QueryStruct


class ForwardGeocoder:
    """ Main class responsible for place search.
    """

    def __init__(self, conn: SearchConnection,
                 params: SearchDetails, timeout: Optional[int]) -> None:
        self.conn = conn
        self.params = params
        self.timeout = dt.timedelta(seconds=timeout or 1000000)
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
        query.compute_direction_penalty()
        log().var_dump('Query direction penalty',
                       lambda: f"[{'LR' if query.dir_penalty < 0 else 'RL'}] {query.dir_penalty}")

        searches: List[AbstractSearch] = []
        if query.num_token_slots() > 0:
            # 2. Compute all possible search interpretations
            log().section('Compute abstract searches')
            search_builder = SearchBuilder(query, self.params)
            num_searches = 0
            for assignment in yield_token_assignments(query):
                searches.extend(search_builder.build(assignment))
                if num_searches < len(searches):
                    log().table_dump('Searches for assignment',
                                     _dump_searches(searches, query, num_searches))
                num_searches = len(searches)
            searches.sort(key=lambda s: (s.penalty, s.SEARCH_PRIO))

        return query, searches

    async def execute_searches(self, query: QueryStruct,
                               searches: List[AbstractSearch]) -> SearchResults:
        """ Run the abstract searches against the database until a result
            is found.
        """
        log().section('Execute database searches')
        results: Dict[Any, SearchResult] = {}

        end_time = dt.datetime.now() + self.timeout

        min_ranking = searches[0].penalty + 2.0
        prev_penalty = 0.0
        for i, search in enumerate(searches):
            if search.penalty > prev_penalty and (search.penalty > min_ranking or i > 15):
                break
            log().table_dump(f"{i + 1}. Search", _dump_searches([search], query))
            log().var_dump('Params', self.params)
            lookup_results = await search.lookup(self.conn, self.params)
            for result in lookup_results:
                rhash = (result.source_table, result.place_id,
                         result.housenumber, result.country_code)
                prevresult = results.get(rhash)
                if prevresult:
                    prevresult.accuracy = min(prevresult.accuracy, result.accuracy)
                else:
                    results[rhash] = result
                min_ranking = min(min_ranking, result.accuracy * 1.2, 2.0)
            log().result_dump('Results', ((r.accuracy, r) for r in lookup_results))
            prev_penalty = search.penalty
            if dt.datetime.now() >= end_time:
                break

        return SearchResults(results.values())

    def pre_filter_results(self, results: SearchResults) -> SearchResults:
        """ Remove results that are significantly worse than the
            best match.
        """
        if results:
            max_ranking = min(r.ranking for r in results) + 0.5
            results = SearchResults(r for r in results if r.ranking < max_ranking)

        return results

    def sort_and_cut_results(self, results: SearchResults) -> SearchResults:
        """ Remove badly matching results, sort by ranking and
            limit to the configured number of results.
        """
        results.sort(key=lambda r: (r.ranking, 0 if r.bbox is None else -r.bbox.area))

        final = SearchResults()
        min_rank = results[0].rank_search
        min_ranking = results[0].ranking

        for r in results:
            if r.ranking + 0.03 * (r.rank_search - min_rank) < min_ranking + 0.5:
                final.append(r)
                min_rank = min(r.rank_search, min_rank)
            if len(final) == self.limit:
                break

        return final

    def rerank_by_query(self, query: QueryStruct, results: SearchResults) -> None:
        """ Adjust the accuracy of the localized result according to how well
            they match the original query.
        """
        assert self.query_analyzer is not None
        qwords = [word for phrase in query.source
                  for word in re.split('[-,: ]+', phrase.text) if word]
        if not qwords:
            return

        for result in results:
            # Negative importance indicates ordering by distance, which is
            # more important than word matching.
            if not result.display_name\
               or (result.importance is not None and result.importance < 0):
                continue
            distance = 0.0
            norm = self.query_analyzer.normalize_text(' '.join((result.display_name,
                                                                result.country_code or '')))
            words = set((w for w in re.split('[-,: ]+', norm) if w))
            if not words:
                continue
            for qword in qwords:
                # only add distance penalty if there is no perfect match
                if qword not in words:
                    wdist = max(difflib.SequenceMatcher(a=qword, b=w).quick_ratio() for w in words)
                    distance += len(qword) if wdist < 0.4 else 1
            # Compensate for the fact that country names do not get a
            # match penalty yet by the tokenizer.
            # Temporary hack that needs to be removed!
            if result.rank_address == 4:
                distance *= 2
            result.accuracy += distance * 0.3 / sum(len(w) for w in qwords)

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
                results = self.pre_filter_results(results)
                await add_result_details(self.conn, results, self.params)
                log().result_dump('Preliminary Results', ((r.accuracy, r) for r in results))
                results = self.sort_and_cut_results(results)
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
            results = self.pre_filter_results(results)
            await add_result_details(self.conn, results, self.params)
            log().result_dump('Preliminary Results', ((r.accuracy, r) for r in results))
            if len(results) > 1:
                self.rerank_by_query(query, results)
                log().result_dump('Results after reranking', ((r.accuracy, r) for r in results))
                results = self.sort_and_cut_results(results)
            log().result_dump('Final Results', ((r.accuracy, r) for r in results))

        return results


def _dump_searches(searches: List[AbstractSearch], query: QueryStruct,
                   start: int = 0) -> Iterator[Optional[List[Any]]]:
    yield ['Penalty', 'Lookups', 'Housenr', 'Postcode', 'Countries',
           'Qualifier', 'Catgeory', 'Rankings']

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

    def fmt_lookup(lk: Any) -> str:
        if not lk:
            return ''

        return f"{lk.lookup_type.__name__}({lk.column}{tk(lk.tokens)})"

    def fmt_cstr(c: Any) -> str:
        if not c:
            return ''

        return f'{c[0]}^{c[1]}'

    for search in searches[start:]:
        fields = ('lookups', 'rankings', 'countries', 'housenumbers',
                  'postcodes', 'qualifiers')
        if hasattr(search, 'search'):
            iters = itertools.zip_longest([f"{search.penalty:.3g}"],
                                          *(getattr(search.search, attr, []) for attr in fields),
                                          getattr(search, 'categories', []),
                                          fillvalue='')
        else:
            iters = itertools.zip_longest([f"{search.penalty:.3g}"],
                                          *(getattr(search, attr, []) for attr in fields),
                                          [],
                                          fillvalue='')
        for penalty, lookup, rank, cc, hnr, pc, qual, cat in iters:
            yield [penalty, fmt_lookup(lookup), fmt_cstr(hnr),
                   fmt_cstr(pc), fmt_cstr(cc), fmt_cstr(qual), fmt_cstr(cat), fmt_ranking(rank)]
        yield None
