# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of a category search around a place.
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


class NearSearch(base.AbstractSearch):
    """ Category search of a place type near the result of another search.
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
        base = await self.search.lookup(conn, details)

        if not base:
            return results

        base.sort(key=lambda r: (r.accuracy, r.rank_search))
        max_accuracy = base[0].accuracy + 0.5
        if base[0].rank_address == 0:
            min_rank = 0
            max_rank = 0
        elif base[0].rank_address < 26:
            min_rank = 1
            max_rank = min(25, base[0].rank_address + 4)
        else:
            min_rank = 26
            max_rank = 30
        base = nres.SearchResults(r for r in base
                                  if (r.source_table == nres.SourceTable.PLACEX
                                      and r.accuracy <= max_accuracy
                                      and r.bbox and r.bbox.area < 20
                                      and r.rank_address >= min_rank
                                      and r.rank_address <= max_rank))

        if base:
            baseids = [b.place_id for b in base[:5] if b.place_id]

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
        for row in await conn.execute(sql, bind_params):
            result = nres.create_from_placex_row(row, nres.SearchResult)
            assert result
            result.accuracy = self.penalty + penalty
            result.bbox = Bbox.from_wkb(row.bbox)
            results.append(result)
