# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of search for an address (search with housenumber).
"""
from typing import cast, List, AsyncIterator

import sqlalchemy as sa

from . import base
from ...typing import SaBind, SaExpression, SaColumn, SaFromClause, SaScalarSelect
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


def _int_list_to_subquery(inp: List[int]) -> 'sa.Subquery':
    """ Create a subselect that returns the given list of integers
        as rows in the column 'nr'.
    """
    vtab = sa.func.JsonArrayEach(sa.type_coerce(inp, sa.JSON))\
             .table_valued(sa.column('value', type_=sa.JSON))
    return sa.select(sa.cast(sa.cast(vtab.c.value, sa.Text), sa.Integer).label('nr')).subquery()


def _interpolated_position(table: SaFromClause, nr: SaColumn) -> SaColumn:
    pos = sa.cast(nr - table.c.startnumber, sa.Float) / (table.c.endnumber - table.c.startnumber)
    return sa.case(
            (table.c.endnumber == table.c.startnumber, table.c.linegeo.ST_Centroid()),
            else_=table.c.linegeo.ST_LineInterpolatePoint(pos)).label('centroid')


def _make_interpolation_subquery(table: SaFromClause, inner: SaFromClause,
                                 numerals: List[int], details: SearchDetails) -> SaScalarSelect:
    all_ids = sa.func.ArrayAgg(table.c.place_id)
    sql = sa.select(all_ids).where(table.c.parent_place_id == inner.c.place_id)

    if len(numerals) == 1:
        sql = sql.where(sa.between(numerals[0], table.c.startnumber, table.c.endnumber))\
                 .where((numerals[0] - table.c.startnumber) % table.c.step == 0)
    else:
        sql = sql.where(sa.or_(
                *(sa.and_(sa.between(n, table.c.startnumber, table.c.endnumber),
                          (n - table.c.startnumber) % table.c.step == 0)
                  for n in numerals)))

    if details.excluded:
        sql = sql.where(base.exclude_places(table))

    return sql.scalar_subquery()


async def _get_placex_housenumbers(conn: SearchConnection,
                                   place_ids: List[int],
                                   details: SearchDetails) -> AsyncIterator[nres.SearchResult]:
    t = conn.t.placex
    sql = base.select_placex(t).add_columns(t.c.importance)\
                               .where(t.c.place_id.in_(place_ids))

    if details.geometry_output:
        sql = base.add_geometry_columns(sql, t.c.geometry, details)

    for row in await conn.execute(sql):
        result = nres.create_from_placex_row(row, nres.SearchResult)
        assert result
        result.bbox = Bbox.from_wkb(row.bbox)
        yield result


async def _get_osmline(conn: SearchConnection, place_ids: List[int],
                       numerals: List[int],
                       details: SearchDetails) -> AsyncIterator[nres.SearchResult]:
    t = conn.t.osmline

    values = _int_list_to_subquery(numerals)
    sql = sa.select(t.c.place_id, t.c.osm_id,
                    t.c.parent_place_id, t.c.address,
                    values.c.nr.label('housenumber'),
                    _interpolated_position(t, values.c.nr),
                    t.c.postcode, t.c.country_code)\
            .where(t.c.place_id.in_(place_ids))\
            .join(values, values.c.nr.between(t.c.startnumber, t.c.endnumber))

    if details.geometry_output:
        sub = sql.subquery()
        sql = base.add_geometry_columns(sa.select(sub), sub.c.centroid, details)

    for row in await conn.execute(sql):
        result = nres.create_from_osmline_row(row, nres.SearchResult)
        assert result
        yield result


async def _get_tiger(conn: SearchConnection, place_ids: List[int],
                     numerals: List[int], osm_id: int,
                     details: SearchDetails) -> AsyncIterator[nres.SearchResult]:
    t = conn.t.tiger
    values = _int_list_to_subquery(numerals)
    sql = sa.select(t.c.place_id, t.c.parent_place_id,
                    sa.literal('W').label('osm_type'),
                    sa.literal(osm_id).label('osm_id'),
                    values.c.nr.label('housenumber'),
                    _interpolated_position(t, values.c.nr),
                    t.c.postcode)\
            .where(t.c.place_id.in_(place_ids))\
            .join(values, values.c.nr.between(t.c.startnumber, t.c.endnumber))

    if details.geometry_output:
        sub = sql.subquery()
        sql = base.add_geometry_columns(sa.select(sub), sub.c.centroid, details)

    for row in await conn.execute(sql):
        result = nres.create_from_tiger_row(row, nres.SearchResult)
        assert result
        yield result


class AddressSearch(base.AbstractSearch):
    """ Generic search for an address or named place.
    """
    SEARCH_PRIO = 1

    def __init__(self, extra_penalty: float, sdata: SearchData,
                 expected_count: int, has_address_terms: bool) -> None:
        assert sdata.housenumbers
        super().__init__(sdata.penalty + extra_penalty)
        self.countries = sdata.countries
        self.postcodes = sdata.postcodes
        self.housenumbers = sdata.housenumbers
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
                          .label('importance'),
                        penalty.label('penalty'))

        for lookup in self.lookups:
            sql = sql.where(lookup.sql_condition(t))

        if self.countries:
            sql = sql.where(t.c.country_code.in_(self.countries.values))

        if self.postcodes:
            if self.expected_count > 10000:
                # Many results expected. Restrict by postcode.
                tpc = conn.t.postcode
                sql = sql.where(sa.select(tpc.c.postcode)
                                  .where(tpc.c.postcode.in_(self.postcodes.values))
                                  .where(t.c.centroid.within_distance(tpc.c.geometry, 0.4))
                                  .exists())

        if details.viewbox is not None:
            if details.bounded_viewbox:
                sql = sql.where(t.c.centroid
                                   .intersects(VIEWBOX_PARAM,
                                               use_index=details.viewbox.area < 0.2))

        if details.near is not None and details.near_radius is not None:
            if details.near_radius < 0.1:
                sql = sql.where(t.c.centroid.within_distance(NEAR_PARAM,
                                                             NEAR_RADIUS_PARAM))
            else:
                sql = sql.where(t.c.centroid
                                 .ST_Distance(NEAR_PARAM) < NEAR_RADIUS_PARAM)

        if self.has_address_terms:
            sql = sql.where(t.c.address_rank.between(16, 30))
        else:
            # If no further address terms are given, then the base street must
            # be in the name. No search for named POIs with the given house number.
            sql = sql.where(t.c.address_rank.between(16, 27))

        inner = sql.limit(10000).order_by(sa.desc(sa.text('importance'))).subquery()

        sql = sa.select(inner.c.place_id, inner.c.search_rank, inner.c.address_rank,
                        inner.c.country_code, inner.c.centroid, inner.c.importance,
                        inner.c.penalty)

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
            tpc = conn.t.postcode
            pcs = self.postcodes.values

            pc_near = sa.select(sa.func.min(tpc.c.geometry.ST_Distance(t.c.centroid)))\
                        .where(tpc.c.postcode.in_(pcs))\
                        .scalar_subquery()
            penalty += sa.case((t.c.postcode.in_(pcs), 0.0),
                               else_=sa.func.coalesce(pc_near, cast(SaColumn, 2.0)))

        if details.viewbox is not None and not details.bounded_viewbox:
            penalty += sa.case((t.c.geometry.intersects(VIEWBOX_PARAM, use_index=False), 0.0),
                               (t.c.geometry.intersects(VIEWBOX2_PARAM, use_index=False), 0.5),
                               else_=1.0)

        if details.near is not None:
            sql = sql.add_columns((-tsearch.c.centroid.ST_Distance(NEAR_PARAM))
                                  .label('importance'))
            sql = sql.order_by(sa.desc(sa.text('importance')))
        else:
            sql = sql.order_by(penalty - tsearch.c.importance)
            sql = sql.add_columns(tsearch.c.importance)

        sql = sql.add_columns(penalty.label('accuracy'))\
                 .order_by(sa.text('accuracy'))

        hnr_list = '|'.join(self.housenumbers.values)

        if self.has_address_terms:
            sql = sql.where(sa.or_(tsearch.c.address_rank < 30,
                                   sa.func.RegexpWord(hnr_list, t.c.housenumber)))

        inner = sql.subquery()

        # Housenumbers from placex
        thnr = conn.t.placex.alias('hnr')
        pid_list = sa.func.ArrayAgg(thnr.c.place_id)
        place_sql = sa.select(pid_list)\
                      .where(thnr.c.parent_place_id == inner.c.place_id)\
                      .where(sa.func.RegexpWord(hnr_list, thnr.c.housenumber))\
                      .where(thnr.c.linked_place_id == None)\
                      .where(thnr.c.indexed_status == 0)

        if details.excluded:
            place_sql = place_sql.where(thnr.c.place_id.not_in(sa.bindparam('excluded')))
        if self.qualifiers:
            place_sql = place_sql.where(self.qualifiers.sql_restrict(thnr))

        numerals = [int(n) for n in self.housenumbers.values
                    if n.isdigit() and len(n) < 8]
        interpol_sql: SaColumn
        tiger_sql: SaColumn
        if numerals and \
           (not self.qualifiers or ('place', 'house') in self.qualifiers.values):
            # Housenumbers from interpolations
            interpol_sql = _make_interpolation_subquery(conn.t.osmline, inner,
                                                        numerals, details)
            # Housenumbers from Tiger
            tiger_sql = sa.case((inner.c.country_code == 'us',
                                 _make_interpolation_subquery(conn.t.tiger, inner,
                                                              numerals, details)
                                 ), else_=None)
        else:
            interpol_sql = sa.null()
            tiger_sql = sa.null()

        unsort = sa.select(inner, place_sql.scalar_subquery().label('placex_hnr'),
                           interpol_sql.label('interpol_hnr'),
                           tiger_sql.label('tiger_hnr')).subquery('unsort')
        sql = sa.select(unsort)\
                .order_by(unsort.c.accuracy +
                          sa.case((unsort.c.placex_hnr != None, 0),
                                  (unsort.c.interpol_hnr != None, 0),
                                  (unsort.c.tiger_hnr != None, 0),
                                  else_=1),
                          sa.case((unsort.c.placex_hnr != None, 1),
                                  (unsort.c.interpol_hnr != None, 2),
                                  (unsort.c.tiger_hnr != None, 3),
                                  else_=4))

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
            assert result
            result.bbox = Bbox.from_wkb(row.bbox)
            result.accuracy = row.accuracy
            if row.rank_address < 30:
                if row.placex_hnr:
                    subs = _get_placex_housenumbers(conn, row.placex_hnr, details)
                elif row.interpol_hnr:
                    subs = _get_osmline(conn, row.interpol_hnr, numerals, details)
                elif row.tiger_hnr:
                    subs = _get_tiger(conn, row.tiger_hnr, numerals, row.osm_id, details)
                else:
                    subs = None

                if subs is not None:
                    async for sub in subs:
                        assert sub.housenumber
                        sub.accuracy = result.accuracy
                        if not any(nr in self.housenumbers.values
                                   for nr in sub.housenumber.split(';')):
                            sub.accuracy += 0.6
                        results.append(sub)

                # Only add the street as a result, if it meets all other
                # filter conditions.
                if (not details.excluded or result.place_id not in details.excluded)\
                   and (not self.qualifiers or result.category in self.qualifiers.values)\
                   and result.rank_address >= details.min_rank:
                    result.accuracy += 1.0  # penalty for missing housenumber
                    results.append(result)
            else:
                results.append(result)

        return results
