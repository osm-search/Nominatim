# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of category search.
"""
from typing import List

import sqlalchemy as sa

from . import base
from ..db_search_fields import SearchData
from ... import results as nres
from ...typing import SaBind, SaRow, SaSelect, SaLambdaSelect
from ...sql.sqlalchemy_types import Geometry
from ...connection import SearchConnection
from ...types import SearchDetails, Bbox


LIMIT_PARAM: SaBind = sa.bindparam('limit')
VIEWBOX_PARAM: SaBind = sa.bindparam('viewbox', type_=Geometry)
NEAR_PARAM: SaBind = sa.bindparam('near', type_=Geometry)
NEAR_RADIUS_PARAM: SaBind = sa.bindparam('near_radius')


class PoiSearch(base.AbstractSearch):
    """ Category search in a geographic area.
    """
    def __init__(self, sdata: SearchData) -> None:
        super().__init__(sdata.penalty)
        self.qualifiers = sdata.qualifiers
        self.countries = sdata.countries

    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        bind_params = {
            'limit': details.max_results,
            'viewbox': details.viewbox,
            'near': details.near,
            'near_radius': details.near_radius,
            'excluded': details.excluded
        }

        t = conn.t.placex

        rows: List[SaRow] = []

        if details.near and details.near_radius is not None and details.near_radius < 0.2:
            # simply search in placex table
            def _base_query() -> SaSelect:
                return base.select_placex(t) \
                           .add_columns((-t.c.centroid.ST_Distance(NEAR_PARAM))
                                        .label('importance'))\
                           .where(t.c.linked_place_id == None) \
                           .where(t.c.geometry.within_distance(NEAR_PARAM, NEAR_RADIUS_PARAM)) \
                           .order_by(t.c.centroid.ST_Distance(NEAR_PARAM)) \
                           .limit(LIMIT_PARAM)

            classtype = self.qualifiers.values
            if len(classtype) == 1:
                cclass, ctype = classtype[0]
                sql: SaLambdaSelect = sa.lambda_stmt(
                    lambda: _base_query().where(t.c.class_ == cclass)
                                         .where(t.c.type == ctype))
            else:
                sql = _base_query().where(sa.or_(*(sa.and_(t.c.class_ == cls, t.c.type == typ)
                                                   for cls, typ in classtype)))

            if self.countries:
                sql = sql.where(t.c.country_code.in_(self.countries.values))

            if details.viewbox is not None and details.bounded_viewbox:
                sql = sql.where(t.c.geometry.intersects(VIEWBOX_PARAM))

            rows.extend(await conn.execute(sql, bind_params))
        else:
            # use the class type tables
            for category in self.qualifiers.values:
                table = await conn.get_class_table(*category)
                if table is not None:
                    sql = base.select_placex(t)\
                               .add_columns(t.c.importance)\
                               .join(table, t.c.place_id == table.c.place_id)\
                               .where(t.c.class_ == category[0])\
                               .where(t.c.type == category[1])

                    if details.viewbox is not None and details.bounded_viewbox:
                        sql = sql.where(table.c.centroid.intersects(VIEWBOX_PARAM))

                    if details.near and details.near_radius is not None:
                        sql = sql.order_by(table.c.centroid.ST_Distance(NEAR_PARAM))\
                                 .where(table.c.centroid.within_distance(NEAR_PARAM,
                                                                         NEAR_RADIUS_PARAM))

                    if self.countries:
                        sql = sql.where(t.c.country_code.in_(self.countries.values))

                    sql = sql.limit(LIMIT_PARAM)
                    rows.extend(await conn.execute(sql, bind_params))

        results = nres.SearchResults()
        for row in rows:
            result = nres.create_from_placex_row(row, nres.SearchResult)
            result.accuracy = self.penalty + self.qualifiers.get_penalty((row.class_, row.type))
            result.bbox = Bbox.from_wkb(row.bbox)
            results.append(result)

        return results
