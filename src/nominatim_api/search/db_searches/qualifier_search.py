# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of search for qualifier+address queries like 'Kingston pub'.

Finds a place by name, then searches for nearby POIs of the given category.
The inner place search is restricted to actual places (not POIs) and the
near lookup only proceeds when there is exactly one matching place.
"""
from typing import List, Tuple

import sqlalchemy as sa

from . import base
from ...typing import SaBind
from ...types import SearchDetails, Bbox
from ...connection import SearchConnection
from ... import results as nres
from ..db_search_fields import WeightedCategories


LIMIT_PARAM: SaBind = sa.bindparam('limit')
MIN_RANK_PARAM: SaBind = sa.bindparam('min_rank')
MAX_RANK_PARAM: SaBind = sa.bindparam('max_rank')
COUNTRIES_PARAM: SaBind = sa.bindparam('countries')


class QualifierNearSearch(base.AbstractSearch):
    """ Search for unnamed POIs of a qualifier category near a small place.

        This handles queries like 'Kingston pub' where a qualifier word
        (pub) is combined with an address (Kingston) but there is no
        explicit name. The inner search finds the place, and the outer
        search finds nearby POIs of the qualifier category.

        Unlike NearSearch, this search:
        - restricts the inner results to actual places (rank_address < 30)
        - only proceeds when there is a single matching place
        - applies penalties for named POIs and for multiple category results
    """
    def __init__(self, penalty: float, categories: WeightedCategories,
                 search: base.AbstractSearch) -> None:
        super().__init__(penalty)
        self.search = search
        self.categories = categories

    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        results = nres.SearchResults()
        base_results = await self.search.lookup(conn, details)

        if not base_results:
            return results

        base_results.sort(key=lambda r: (r.accuracy, r.rank_search))
        max_accuracy = base_results[0].accuracy + 0.5

        # Restrict to actual places (rank_address < 30), not POIs.
        base_results = nres.SearchResults(
            r for r in base_results
            if (r.source_table == nres.SourceTable.PLACEX
                and r.accuracy <= max_accuracy
                and r.bbox and r.bbox.area < 5.0
                and r.rank_address >= 1
                and r.rank_address < 30))

        # Only proceed if there is exactly one matching place.
        if len(base_results) != 1:
            return results

        baseids = [b.place_id for b in base_results if b.place_id]

        for category, penalty in self.categories:
            await self.lookup_category(results, conn, baseids, category, penalty, details)
            if len(results) >= details.max_results:
                break

        return results

    async def lookup_category(self, results: nres.SearchResults,
                              conn: SearchConnection, ids: List[int],
                              category: Tuple[str, str], penalty: float,
                              details: SearchDetails) -> None:
        """ Find places of the given category near the list of
            place ids and add the results to 'results'.
        """
        table = await conn.get_class_table(*category)

        tgeom = conn.t.placex.alias('pgeom')

        if table is None:
            # No classtype table available, do a simplified lookup in placex.
            table = conn.t.placex
            sql = sa.select(table.c.place_id,
                            sa.func.min(tgeom.c.centroid.ST_Distance(table.c.centroid))
                              .label('dist'))\
                    .join(tgeom, table.c.geometry.intersects(tgeom.c.centroid.ST_Expand(0.01)))\
                    .where(table.c.class_ == category[0])\
                    .where(table.c.type == category[1])
        else:
            # Use classtype table. We can afford to use a larger
            # radius for the lookup.
            sql = sa.select(table.c.place_id,
                            sa.func.min(tgeom.c.centroid.ST_Distance(table.c.centroid))
                              .label('dist'))\
                    .join(tgeom,
                          table.c.centroid.ST_CoveredBy(
                              sa.case((sa.and_(tgeom.c.rank_address > 9,
                                               tgeom.c.geometry.is_area()),
                                       tgeom.c.geometry),
                                      else_=tgeom.c.centroid.ST_Expand(0.05))))

        inner = sql.where(tgeom.c.place_id.in_(ids))\
                   .group_by(table.c.place_id).subquery()

        t = conn.t.placex
        sql = base.select_placex(t).add_columns((-inner.c.dist).label('importance'))\
                                   .join(inner, inner.c.place_id == t.c.place_id)\
                                   .order_by(inner.c.dist)

        sql = sql.where(base.no_index(t.c.rank_address).between(MIN_RANK_PARAM, MAX_RANK_PARAM))
        if details.countries:
            sql = sql.where(t.c.country_code.in_(COUNTRIES_PARAM))
        if details.excluded:
            sql = sql.where(base.exclude_places(t))
        if details.layers is not None:
            sql = sql.where(base.filter_by_layer(t, details.layers))

        sql = sql.limit(LIMIT_PARAM)

        bind_params = {'limit': details.max_results,
                       'min_rank': details.min_rank,
                       'max_rank': details.max_rank,
                       'excluded': details.excluded,
                       'countries': details.countries}
        new_results = []
        for row in await conn.execute(sql, bind_params):
            result = nres.create_from_placex_row(row, nres.SearchResult)
            result.accuracy = self.penalty + penalty
            # Penalize named POIs: unnamed POIs are expected here.
            if result.names:
                result.accuracy += 0.4
            result.bbox = Bbox.from_wkb(row.bbox)
            new_results.append(result)

        # Penalize when there are multiple results of this category.
        if len(new_results) > 1:
            for result in new_results:
                result.accuracy += 0.2

        results.extend(new_results)
