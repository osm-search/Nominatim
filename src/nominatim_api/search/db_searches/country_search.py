# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of searches for a country.
"""

import sqlalchemy as sa

from . import base
from ..db_search_fields import SearchData
from ... import results as nres
from ...connection import SearchConnection
from ...types import SearchDetails, Bbox


class CountrySearch(base.AbstractSearch):
    """ Search for a country name or country code.
    """
    SEARCH_PRIO = 0

    def __init__(self, sdata: SearchData) -> None:
        super().__init__(sdata.penalty)
        self.countries = sdata.countries

    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        t = conn.t.placex

        ccodes = self.countries.values
        sql = base.select_placex(t)\
            .add_columns(t.c.importance)\
            .where(t.c.country_code.in_(ccodes))\
            .where(t.c.rank_address == 4)

        if details.geometry_output:
            sql = base.add_geometry_columns(sql, t.c.geometry, details)

        if details.excluded:
            sql = sql.where(base.exclude_places(t))

        sql = base.filter_by_area(sql, t, details)

        bind_params = {
            'excluded': details.excluded,
            'viewbox': details.viewbox,
            'near': details.near,
            'near_radius': details.near_radius
        }

        results = nres.SearchResults()
        for row in await conn.execute(sql, bind_params):
            result = nres.create_from_placex_row(row, nres.SearchResult)
            result.accuracy = self.penalty + self.countries.get_penalty(row.country_code, 5.0)
            result.bbox = Bbox.from_wkb(row.bbox)
            results.append(result)

        if not results:
            results = await self.lookup_in_country_table(conn, details)

        if results:
            details.min_rank = min(5, details.max_rank)
            details.max_rank = min(25, details.max_rank)

        return results

    async def lookup_in_country_table(self, conn: SearchConnection,
                                      details: SearchDetails) -> nres.SearchResults:
        """ Look up the country in the fallback country tables.
        """
        # Avoid the fallback search when this is a more search. Country results
        # usually are in the first batch of results and it is not possible
        # to exclude these fallbacks.
        if details.excluded:
            return nres.SearchResults()

        t = conn.t.country_name
        tgrid = conn.t.country_grid

        sql = sa.select(tgrid.c.country_code,
                        tgrid.c.geometry.ST_Centroid().ST_Collect().ST_Centroid()
                             .label('centroid'),
                        tgrid.c.geometry.ST_Collect().ST_Expand(0).label('bbox'))\
                .where(tgrid.c.country_code.in_(self.countries.values))\
                .group_by(tgrid.c.country_code)

        sql = base.filter_by_area(sql, tgrid, details, avoid_index=True)

        sub = sql.subquery('grid')

        sql = sa.select(t.c.country_code,
                        t.c.name.merge(t.c.derived_name).label('name'),
                        sub.c.centroid, sub.c.bbox)\
                .join(sub, t.c.country_code == sub.c.country_code)

        if details.geometry_output:
            sql = base.add_geometry_columns(sql, sub.c.centroid, details)

        bind_params = {
            'viewbox': details.viewbox,
            'near': details.near,
            'near_radius': details.near_radius
        }

        results = nres.SearchResults()
        for row in await conn.execute(sql, bind_params):
            result = nres.create_from_country_row(row, nres.SearchResult)
            result.bbox = Bbox.from_wkb(row.bbox)
            result.accuracy = self.penalty + self.countries.get_penalty(row.country_code, 5.0)
            results.append(result)

        return results
