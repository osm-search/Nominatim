# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of search for a postcode.
"""

import sqlalchemy as sa

from . import base
from ...typing import SaBind, SaExpression
from ...sql.sqlalchemy_types import Geometry, IntArray
from ...connection import SearchConnection
from ...types import SearchDetails, Bbox
from ... import results as nres
from ..db_search_fields import SearchData


LIMIT_PARAM: SaBind = sa.bindparam('limit')
VIEWBOX_PARAM: SaBind = sa.bindparam('viewbox', type_=Geometry)
VIEWBOX2_PARAM: SaBind = sa.bindparam('viewbox2', type_=Geometry)
NEAR_PARAM: SaBind = sa.bindparam('near', type_=Geometry)


class PostcodeSearch(base.AbstractSearch):
    """ Search for a postcode.
    """
    def __init__(self, extra_penalty: float, sdata: SearchData) -> None:
        super().__init__(sdata.penalty + extra_penalty)
        self.countries = sdata.countries
        self.postcodes = sdata.postcodes
        self.lookups = sdata.lookups
        self.rankings = sdata.rankings

    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        t = conn.t.postcode
        pcs = self.postcodes.values

        sql = sa.select(t.c.place_id, t.c.parent_place_id,
                        t.c.rank_search, t.c.rank_address,
                        t.c.postcode, t.c.country_code,
                        t.c.geometry.label('centroid'))\
                .where(t.c.postcode.in_(pcs))

        if details.geometry_output:
            sql = base.add_geometry_columns(sql, t.c.geometry, details)

        penalty: SaExpression = sa.literal(self.penalty)

        if details.viewbox is not None and not details.bounded_viewbox:
            penalty += sa.case((t.c.geometry.intersects(VIEWBOX_PARAM), 0.0),
                               (t.c.geometry.intersects(VIEWBOX2_PARAM), 0.5),
                               else_=1.0)

        if details.near is not None:
            sql = sql.order_by(t.c.geometry.ST_Distance(NEAR_PARAM))

        sql = base.filter_by_area(sql, t, details)

        if self.countries:
            sql = sql.where(t.c.country_code.in_(self.countries.values))

        if details.excluded:
            sql = sql.where(base.exclude_places(t))

        if self.lookups:
            assert len(self.lookups) == 1
            tsearch = conn.t.search_name
            sql = sql.where(tsearch.c.place_id == t.c.parent_place_id)\
                     .where((tsearch.c.name_vector + tsearch.c.nameaddress_vector)
                            .contains(sa.type_coerce(self.lookups[0].tokens,
                                                     IntArray)))
            # Do NOT add rerank penalties based on the address terms.
            # The standard rerank penalty only checks the address vector
            # while terms may appear in name and address vector. This would
            # lead to overly high penalties.
            # We assume that a postcode is precise enough to not require
            # additional full name matches.

        penalty += sa.case(*((t.c.postcode == v, p) for v, p in self.postcodes),
                           else_=1.0)

        sql = sql.add_columns(penalty.label('accuracy'))
        sql = sql.order_by('accuracy').limit(LIMIT_PARAM)

        bind_params = {
            'limit': details.max_results,
            'viewbox': details.viewbox,
            'viewbox2': details.viewbox_x2,
            'near': details.near,
            'near_radius': details.near_radius,
            'excluded': details.excluded
        }

        results = nres.SearchResults()
        for row in await conn.execute(sql, bind_params):
            p = conn.t.placex
            placex_sql = base.select_placex(p)\
                .add_columns(p.c.importance)\
                .where(sa.text("""class = 'boundary'
                                  AND type = 'postal_code'
                                  AND osm_type = 'R'"""))\
                .where(p.c.country_code == row.country_code)\
                .where(p.c.postcode == row.postcode)\
                .limit(1)

            if details.geometry_output:
                placex_sql = base.add_geometry_columns(placex_sql, p.c.geometry, details)

            for prow in await conn.execute(placex_sql, bind_params):
                result = nres.create_from_placex_row(prow, nres.SearchResult)
                if result is not None:
                    result.bbox = Bbox.from_wkb(prow.bbox)
                break
            else:
                result = nres.create_from_postcode_row(row, nres.SearchResult)

            if result.place_id not in details.excluded:
                result.accuracy = row.accuracy
                results.append(result)

        return results
