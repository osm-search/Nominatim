# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of search for a named place (without housenumber).
"""
from typing import cast

import sqlalchemy as sa

from . import base
from ...typing import SaBind, SaExpression, SaColumn
from ...types import SearchDetails, Bbox
from ...sql.sqlalchemy_types import Geometry
from ...connection import SearchConnection
from ... import results as nres
from ..db_search_fields import SearchData


LIMIT_PARAM: SaBind = sa.bindparam('limit')
MIN_RANK_PARAM: SaBind = sa.bindparam('min_rank')
MAX_RANK_PARAM: SaBind = sa.bindparam('max_rank')
VIEWBOX_PARAM: SaBind = sa.bindparam('viewbox', type_=Geometry)
VIEWBOX2_PARAM: SaBind = sa.bindparam('viewbox2', type_=Geometry)
NEAR_PARAM: SaBind = sa.bindparam('near', type_=Geometry)
NEAR_RADIUS_PARAM: SaBind = sa.bindparam('near_radius')
COUNTRIES_PARAM: SaBind = sa.bindparam('countries')


class PlaceSearch(base.AbstractSearch):
    """ Generic search for a named place.
    """
    SEARCH_PRIO = 1

    def __init__(self, extra_penalty: float, sdata: SearchData,
                 expected_count: int, has_address_terms: bool) -> None:
        assert not sdata.housenumbers
        super().__init__(sdata.penalty + extra_penalty)
        self.countries = sdata.countries
        self.postcodes = sdata.postcodes
        self.qualifiers = sdata.qualifiers
        self.lookups = sdata.lookups
        self.rankings = sdata.rankings
        self.expected_count = expected_count
        self.has_address_terms = has_address_terms

    def _inner_search_name_cte(self, conn: SearchConnection,
                               details: SearchDetails) -> 'sa.CTE':
        """ Create a subquery that preselects the rows in the search_name
            table.
        """
        t = conn.t.search_name

        penalty: SaExpression = sa.literal(self.penalty)
        for ranking in self.rankings:
            penalty += ranking.sql_penalty(t)

        sql = sa.select(t.c.place_id, t.c.search_rank, t.c.address_rank,
                        t.c.country_code, t.c.centroid,
                        t.c.name_vector, t.c.nameaddress_vector,
                        sa.case((t.c.importance > 0, t.c.importance),
                                else_=0.40001-(sa.cast(t.c.search_rank, sa.Float())/75))
                          .label('importance'))

        for lookup in self.lookups:
            sql = sql.where(lookup.sql_condition(t))

        if self.countries:
            sql = sql.where(t.c.country_code.in_(self.countries.values))

        if self.postcodes:
            # if a postcode is given, don't search for state or country level objects
            sql = sql.where(t.c.address_rank > 9)
            if self.expected_count > 10000:
                # Many results expected. Restrict by postcode.
                tpc = conn.t.postcode
                sql = sql.where(sa.select(tpc.c.postcode)
                                  .where(tpc.c.postcode.in_(self.postcodes.values))
                                  .where(t.c.centroid.intersects(tpc.c.geometry,
                                                                 use_index=False))
                                  .exists())

        if details.viewbox is not None:
            if details.bounded_viewbox:
                sql = sql.where(t.c.centroid
                                   .intersects(VIEWBOX_PARAM,
                                               use_index=details.viewbox.area < 0.2))
            else:
                penalty += sa.case((t.c.centroid.intersects(VIEWBOX_PARAM, use_index=False), 0.0),
                                   (t.c.centroid.intersects(VIEWBOX2_PARAM, use_index=False), 0.5),
                                   else_=1.0)

        if details.near is not None and details.near_radius is not None:
            if details.near_radius < 0.1:
                sql = sql.where(t.c.centroid.within_distance(NEAR_PARAM,
                                                             NEAR_RADIUS_PARAM))
            else:
                sql = sql.where(t.c.centroid
                                 .ST_Distance(NEAR_PARAM) < NEAR_RADIUS_PARAM)

        if details.excluded:
            sql = sql.where(base.exclude_places(t))
        if details.min_rank > 0:
            sql = sql.where(sa.or_(t.c.address_rank >= MIN_RANK_PARAM,
                                   t.c.search_rank >= MIN_RANK_PARAM))
        if details.max_rank < 30:
            sql = sql.where(sa.or_(t.c.address_rank <= MAX_RANK_PARAM,
                                   t.c.search_rank <= MAX_RANK_PARAM))

        sql = sql.add_columns(penalty.label('penalty'))

        inner = sql.limit(5000 if self.qualifiers else 1000)\
                   .order_by(sa.desc(sa.text('importance')))\
                   .subquery()

        sql = sa.select(inner.c.place_id, inner.c.search_rank, inner.c.address_rank,
                        inner.c.country_code, inner.c.centroid, inner.c.importance,
                        inner.c.penalty)

        # If the query is not an address search or has a geographic preference,
        # preselect most important items to restrict the number of places
        # that need to be looked up in placex.
        if (details.viewbox is None or not details.bounded_viewbox)\
           and (details.near is None or details.near_radius is None)\
           and not self.qualifiers:
            sql = sql.add_columns(sa.func.first_value(inner.c.penalty - inner.c.importance)
                                    .over(order_by=inner.c.penalty - inner.c.importance)
                                    .label('min_penalty'))

            inner = sql.subquery()

            sql = sa.select(inner.c.place_id, inner.c.search_rank, inner.c.address_rank,
                            inner.c.country_code, inner.c.centroid, inner.c.importance,
                            inner.c.penalty)\
                    .where(inner.c.penalty - inner.c.importance < inner.c.min_penalty + 0.5)

        return sql.cte('searches')

    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        t = conn.t.placex
        tsearch = self._inner_search_name_cte(conn, details)

        sql = base.select_placex(t).join(tsearch, t.c.place_id == tsearch.c.place_id)

        if details.geometry_output:
            sql = base.add_geometry_columns(sql, t.c.geometry, details)

        penalty: SaExpression = tsearch.c.penalty

        if self.postcodes:
            if self.has_address_terms:
                tpc = conn.t.postcode
                pcs = self.postcodes.values

                pc_near = sa.select(sa.func.min(tpc.c.centroid.ST_Distance(t.c.centroid)))\
                            .where(tpc.c.postcode.in_(pcs))\
                            .scalar_subquery()
                penalty += sa.case((t.c.postcode.in_(pcs), 0.0),
                                   else_=sa.func.coalesce(pc_near, cast(SaColumn, 2.0)))
            else:
                # High penalty if the postcode is not an exact match.
                # The postcode search needs to get priority here.
                penalty += sa.case((t.c.postcode.in_(self.postcodes.values), 0.0), else_=1.0)

        if details.near is not None:
            sql = sql.add_columns((-tsearch.c.centroid.ST_Distance(NEAR_PARAM))
                                  .label('importance'))
            sql = sql.order_by(sa.desc(sa.text('importance')))
        else:
            sql = sql.order_by(penalty - tsearch.c.importance)
            sql = sql.add_columns(tsearch.c.importance)

        sql = sql.add_columns(penalty.label('accuracy'))\
                 .order_by(sa.text('accuracy'))

        sql = sql.where(t.c.linked_place_id == None)\
                 .where(t.c.indexed_status == 0)
        if self.qualifiers:
            sql = sql.where(self.qualifiers.sql_restrict(t))
        if details.layers is not None:
            sql = sql.where(base.filter_by_layer(t, details.layers))

        sql = sql.limit(LIMIT_PARAM)

        bind_params = {
            'limit': details.max_results,
            'min_rank': details.min_rank,
            'max_rank': details.max_rank,
            'viewbox': details.viewbox,
            'viewbox2': details.viewbox_x2,
            'near': details.near,
            'near_radius': details.near_radius,
            'excluded': details.excluded,
            'countries': details.countries
        }

        results = nres.SearchResults()
        for row in await conn.execute(sql, bind_params):
            result = nres.create_from_placex_row(row, nres.SearchResult)
            result.bbox = Bbox.from_wkb(row.bbox)
            result.accuracy = row.accuracy
            results.append(result)

        return results
