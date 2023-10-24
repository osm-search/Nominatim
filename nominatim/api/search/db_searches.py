# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the acutal database accesses for forward search.
"""
from typing import List, Tuple, AsyncIterator, Dict, Any, Callable
import abc

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, array_agg

from nominatim.typing import SaFromClause, SaScalarSelect, SaColumn, \
                             SaExpression, SaSelect, SaLambdaSelect, SaRow, SaBind
from nominatim.api.connection import SearchConnection
from nominatim.api.types import SearchDetails, DataLayer, GeometryFormat, Bbox
import nominatim.api.results as nres
from nominatim.api.search.db_search_fields import SearchData, WeightedCategories
from nominatim.db.sqlalchemy_types import Geometry

#pylint: disable=singleton-comparison,not-callable
#pylint: disable=too-many-branches,too-many-arguments,too-many-locals,too-many-statements

def _details_to_bind_params(details: SearchDetails) -> Dict[str, Any]:
    """ Create a dictionary from search parameters that can be used
        as bind parameter for SQL execute.
    """
    return {'limit': details.max_results,
            'min_rank': details.min_rank,
            'max_rank': details.max_rank,
            'viewbox': details.viewbox,
            'viewbox2': details.viewbox_x2,
            'near': details.near,
            'near_radius': details.near_radius,
            'excluded': details.excluded,
            'countries': details.countries}


LIMIT_PARAM: SaBind = sa.bindparam('limit')
MIN_RANK_PARAM: SaBind = sa.bindparam('min_rank')
MAX_RANK_PARAM: SaBind = sa.bindparam('max_rank')
VIEWBOX_PARAM: SaBind = sa.bindparam('viewbox', type_=Geometry)
VIEWBOX2_PARAM: SaBind = sa.bindparam('viewbox2', type_=Geometry)
NEAR_PARAM: SaBind = sa.bindparam('near', type_=Geometry)
NEAR_RADIUS_PARAM: SaBind = sa.bindparam('near_radius')
COUNTRIES_PARAM: SaBind = sa.bindparam('countries')

def _within_near(t: SaFromClause) -> Callable[[], SaExpression]:
    return lambda: t.c.geometry.ST_DWithin(NEAR_PARAM, NEAR_RADIUS_PARAM)

def _exclude_places(t: SaFromClause) -> Callable[[], SaExpression]:
    return lambda: t.c.place_id.not_in(sa.bindparam('excluded'))

def _select_placex(t: SaFromClause) -> SaSelect:
    return sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                     t.c.class_, t.c.type,
                     t.c.address, t.c.extratags,
                     t.c.housenumber, t.c.postcode, t.c.country_code,
                     t.c.importance, t.c.wikipedia,
                     t.c.parent_place_id, t.c.rank_address, t.c.rank_search,
                     t.c.linked_place_id, t.c.admin_level,
                     t.c.centroid,
                     t.c.geometry.ST_Expand(0).label('bbox'))


def _add_geometry_columns(sql: SaLambdaSelect, col: SaColumn, details: SearchDetails) -> SaSelect:
    out = []

    if details.geometry_simplification > 0.0:
        col = sa.func.ST_SimplifyPreserveTopology(col, details.geometry_simplification)

    if details.geometry_output & GeometryFormat.GEOJSON:
        out.append(sa.func.ST_AsGeoJSON(col, 7).label('geometry_geojson'))
    if details.geometry_output & GeometryFormat.TEXT:
        out.append(sa.func.ST_AsText(col).label('geometry_text'))
    if details.geometry_output & GeometryFormat.KML:
        out.append(sa.func.ST_AsKML(col, 7).label('geometry_kml'))
    if details.geometry_output & GeometryFormat.SVG:
        out.append(sa.func.ST_AsSVG(col, 0, 7).label('geometry_svg'))

    return sql.add_columns(*out)


def _make_interpolation_subquery(table: SaFromClause, inner: SaFromClause,
                                 numerals: List[int], details: SearchDetails) -> SaScalarSelect:
    all_ids = array_agg(table.c.place_id) # type: ignore[no-untyped-call]
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
        sql = sql.where(_exclude_places(table))

    return sql.scalar_subquery()


def _filter_by_layer(table: SaFromClause, layers: DataLayer) -> SaColumn:
    orexpr: List[SaExpression] = []
    if layers & DataLayer.ADDRESS and layers & DataLayer.POI:
        orexpr.append(table.c.rank_address.between(1, 30))
    elif layers & DataLayer.ADDRESS:
        orexpr.append(table.c.rank_address.between(1, 29))
        orexpr.append(sa.and_(table.c.rank_address == 30,
                              sa.or_(table.c.housenumber != None,
                                     table.c.address.has_key('addr:housename'))))
    elif layers & DataLayer.POI:
        orexpr.append(sa.and_(table.c.rank_address == 30,
                              table.c.class_.not_in(('place', 'building'))))

    if layers & DataLayer.MANMADE:
        exclude = []
        if not layers & DataLayer.RAILWAY:
            exclude.append('railway')
        if not layers & DataLayer.NATURAL:
            exclude.extend(('natural', 'water', 'waterway'))
        orexpr.append(sa.and_(table.c.class_.not_in(tuple(exclude)),
                              table.c.rank_address == 0))
    else:
        include = []
        if layers & DataLayer.RAILWAY:
            include.append('railway')
        if layers & DataLayer.NATURAL:
            include.extend(('natural', 'water', 'waterway'))
        orexpr.append(sa.and_(table.c.class_.in_(tuple(include)),
                              table.c.rank_address == 0))

    if len(orexpr) == 1:
        return orexpr[0]

    return sa.or_(*orexpr)


def _interpolated_position(table: SaFromClause, nr: SaColumn) -> SaColumn:
    pos = sa.cast(nr - table.c.startnumber, sa.Float) / (table.c.endnumber - table.c.startnumber)
    return sa.case(
            (table.c.endnumber == table.c.startnumber, table.c.linegeo.ST_Centroid()),
            else_=table.c.linegeo.ST_LineInterpolatePoint(pos)).label('centroid')


async def _get_placex_housenumbers(conn: SearchConnection,
                                   place_ids: List[int],
                                   details: SearchDetails) -> AsyncIterator[nres.SearchResult]:
    t = conn.t.placex
    sql = _select_placex(t).where(t.c.place_id.in_(place_ids))

    if details.geometry_output:
        sql = _add_geometry_columns(sql, t.c.geometry, details)

    for row in await conn.execute(sql):
        result = nres.create_from_placex_row(row, nres.SearchResult)
        assert result
        result.bbox = Bbox.from_wkb(row.bbox)
        yield result


async def _get_osmline(conn: SearchConnection, place_ids: List[int],
                       numerals: List[int],
                       details: SearchDetails) -> AsyncIterator[nres.SearchResult]:
    t = conn.t.osmline
    values = sa.values(sa.Column('nr', sa.Integer()), name='housenumber')\
               .data([(n,) for n in numerals])
    sql = sa.select(t.c.place_id, t.c.osm_id,
                    t.c.parent_place_id, t.c.address,
                    values.c.nr.label('housenumber'),
                    _interpolated_position(t, values.c.nr),
                    t.c.postcode, t.c.country_code)\
            .where(t.c.place_id.in_(place_ids))\
            .join(values, values.c.nr.between(t.c.startnumber, t.c.endnumber))

    if details.geometry_output:
        sub = sql.subquery()
        sql = _add_geometry_columns(sa.select(sub), sub.c.centroid, details)

    for row in await conn.execute(sql):
        result = nres.create_from_osmline_row(row, nres.SearchResult)
        assert result
        yield result


async def _get_tiger(conn: SearchConnection, place_ids: List[int],
                     numerals: List[int], osm_id: int,
                     details: SearchDetails) -> AsyncIterator[nres.SearchResult]:
    t = conn.t.tiger
    values = sa.values(sa.Column('nr', sa.Integer()), name='housenumber')\
               .data([(n,) for n in numerals])
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
        sql = _add_geometry_columns(sa.select(sub), sub.c.centroid, details)

    for row in await conn.execute(sql):
        result = nres.create_from_tiger_row(row, nres.SearchResult)
        assert result
        yield result


class AbstractSearch(abc.ABC):
    """ Encapuslation of a single lookup in the database.
    """

    def __init__(self, penalty: float) -> None:
        self.penalty = penalty

    @abc.abstractmethod
    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """


class NearSearch(AbstractSearch):
    """ Category search of a place type near the result of another search.
    """
    def __init__(self, penalty: float, categories: WeightedCategories,
                 search: AbstractSearch) -> None:
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
        base = nres.SearchResults(r for r in base if r.source_table == nres.SourceTable.PLACEX
                                                     and r.accuracy <= max_accuracy
                                                     and r.bbox and r.bbox.area < 20)

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

        t = conn.t.placex
        tgeom = conn.t.placex.alias('pgeom')

        sql = _select_placex(t).where(tgeom.c.place_id.in_(ids))\
                               .where(t.c.class_ == category[0])\
                               .where(t.c.type == category[1])

        if table is None:
            # No classtype table available, do a simplified lookup in placex.
            sql = sql.join(tgeom, t.c.geometry.ST_DWithin(tgeom.c.centroid, 0.01))\
                     .order_by(tgeom.c.centroid.ST_Distance(t.c.centroid))
        else:
            # Use classtype table. We can afford to use a larger
            # radius for the lookup.
            sql = sql.join(table, t.c.place_id == table.c.place_id)\
                     .join(tgeom,
                           table.c.centroid.ST_CoveredBy(
                               sa.case((sa.and_(tgeom.c.rank_address < 9,
                                                tgeom.c.geometry.is_area()),
                                        tgeom.c.geometry),
                                       else_ = tgeom.c.centroid.ST_Expand(0.05))))\
                     .order_by(tgeom.c.centroid.ST_Distance(table.c.centroid))

        sql = sql.where(t.c.rank_address.between(MIN_RANK_PARAM, MAX_RANK_PARAM))
        if details.countries:
            sql = sql.where(t.c.country_code.in_(COUNTRIES_PARAM))
        if details.excluded:
            sql = sql.where(_exclude_places(t))
        if details.layers is not None:
            sql = sql.where(_filter_by_layer(t, details.layers))

        sql = sql.limit(LIMIT_PARAM)
        for row in await conn.execute(sql, _details_to_bind_params(details)):
            result = nres.create_from_placex_row(row, nres.SearchResult)
            assert result
            result.accuracy = self.penalty + penalty
            result.bbox = Bbox.from_wkb(row.bbox)
            results.append(result)



class PoiSearch(AbstractSearch):
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
        bind_params = _details_to_bind_params(details)
        t = conn.t.placex

        rows: List[SaRow] = []

        if details.near and details.near_radius is not None and details.near_radius < 0.2:
            # simply search in placex table
            def _base_query() -> SaSelect:
                return _select_placex(t) \
                           .where(t.c.linked_place_id == None) \
                           .where(t.c.geometry.ST_DWithin(NEAR_PARAM, NEAR_RADIUS_PARAM)) \
                           .order_by(t.c.centroid.ST_Distance(NEAR_PARAM)) \
                           .limit(LIMIT_PARAM)

            classtype = self.qualifiers.values
            if len(classtype) == 1:
                cclass, ctype = classtype[0]
                sql: SaLambdaSelect = sa.lambda_stmt(lambda: _base_query()
                                                 .where(t.c.class_ == cclass)
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
                    sql = _select_placex(t)\
                               .join(table, t.c.place_id == table.c.place_id)\
                               .where(t.c.class_ == category[0])\
                               .where(t.c.type == category[1])

                    if details.viewbox is not None and details.bounded_viewbox:
                        sql = sql.where(table.c.centroid.intersects(VIEWBOX_PARAM))

                    if details.near and details.near_radius is not None:
                        sql = sql.order_by(table.c.centroid.ST_Distance(NEAR_PARAM))\
                                 .where(table.c.centroid.ST_DWithin(NEAR_PARAM,
                                                                    NEAR_RADIUS_PARAM))

                    if self.countries:
                        sql = sql.where(t.c.country_code.in_(self.countries.values))

                    sql = sql.limit(LIMIT_PARAM)
                    rows.extend(await conn.execute(sql, bind_params))

        results = nres.SearchResults()
        for row in rows:
            result = nres.create_from_placex_row(row, nres.SearchResult)
            assert result
            result.accuracy = self.penalty + self.qualifiers.get_penalty((row.class_, row.type))
            result.bbox = Bbox.from_wkb(row.bbox)
            results.append(result)

        return results


class CountrySearch(AbstractSearch):
    """ Search for a country name or country code.
    """
    def __init__(self, sdata: SearchData) -> None:
        super().__init__(sdata.penalty)
        self.countries = sdata.countries


    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        t = conn.t.placex

        ccodes = self.countries.values
        sql = _select_placex(t)\
                .where(t.c.country_code.in_(ccodes))\
                .where(t.c.rank_address == 4)

        if details.geometry_output:
            sql = _add_geometry_columns(sql, t.c.geometry, details)

        if details.excluded:
            sql = sql.where(_exclude_places(t))

        if details.viewbox is not None and details.bounded_viewbox:
            sql = sql.where(lambda: t.c.geometry.intersects(VIEWBOX_PARAM))

        if details.near is not None and details.near_radius is not None:
            sql = sql.where(_within_near(t))

        results = nres.SearchResults()
        for row in await conn.execute(sql, _details_to_bind_params(details)):
            result = nres.create_from_placex_row(row, nres.SearchResult)
            assert result
            result.accuracy = self.penalty + self.countries.get_penalty(row.country_code, 5.0)
            result.bbox = Bbox.from_wkb(row.bbox)
            results.append(result)

        return results or await self.lookup_in_country_table(conn, details)


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

        if details.viewbox is not None and details.bounded_viewbox:
            sql = sql.where(tgrid.c.geometry.intersects(VIEWBOX_PARAM))
        if details.near is not None and details.near_radius is not None:
            sql = sql.where(_within_near(tgrid))

        sub = sql.subquery('grid')

        sql = sa.select(t.c.country_code,
                        (t.c.name
                         + sa.func.coalesce(t.c.derived_name,
                                            sa.cast('', type_=conn.t.types.Composite))
                        ).label('name'),
                        sub.c.centroid, sub.c.bbox)\
                .join(sub, t.c.country_code == sub.c.country_code)

        if details.geometry_output:
            sql = _add_geometry_columns(sql, sub.c.centroid, details)

        results = nres.SearchResults()
        for row in await conn.execute(sql, _details_to_bind_params(details)):
            result = nres.create_from_country_row(row, nres.SearchResult)
            assert result
            result.bbox = Bbox.from_wkb(row.bbox)
            result.accuracy = self.penalty + self.countries.get_penalty(row.country_code, 5.0)
            results.append(result)

        return results



class PostcodeSearch(AbstractSearch):
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
            sql = _add_geometry_columns(sql, t.c.geometry, details)

        penalty: SaExpression = sa.literal(self.penalty)

        if details.viewbox is not None:
            if details.bounded_viewbox:
                sql = sql.where(t.c.geometry.intersects(VIEWBOX_PARAM))
            else:
                penalty += sa.case((t.c.geometry.intersects(VIEWBOX_PARAM), 0.0),
                                   (t.c.geometry.intersects(VIEWBOX2_PARAM), 0.5),
                                   else_=1.0)

        if details.near is not None:
            if details.near_radius is not None:
                sql = sql.where(_within_near(t))
            sql = sql.order_by(t.c.geometry.ST_Distance(NEAR_PARAM))

        if self.countries:
            sql = sql.where(t.c.country_code.in_(self.countries.values))

        if details.excluded:
            sql = sql.where(_exclude_places(t))

        if self.lookups:
            assert len(self.lookups) == 1
            assert self.lookups[0].lookup_type == 'restrict'
            tsearch = conn.t.search_name
            sql = sql.where(tsearch.c.place_id == t.c.parent_place_id)\
                     .where(sa.func.array_cat(tsearch.c.name_vector,
                                              tsearch.c.nameaddress_vector,
                                              type_=ARRAY(sa.Integer))
                                    .contains(self.lookups[0].tokens))

        for ranking in self.rankings:
            penalty += ranking.sql_penalty(conn.t.search_name)
        penalty += sa.case(*((t.c.postcode == v, p) for v, p in self.postcodes),
                       else_=1.0)


        sql = sql.add_columns(penalty.label('accuracy'))
        sql = sql.order_by('accuracy').limit(LIMIT_PARAM)

        results = nres.SearchResults()
        for row in await conn.execute(sql, _details_to_bind_params(details)):
            result = nres.create_from_postcode_row(row, nres.SearchResult)
            assert result
            result.accuracy = row.accuracy
            results.append(result)

        return results



class PlaceSearch(AbstractSearch):
    """ Generic search for an address or named place.
    """
    def __init__(self, extra_penalty: float, sdata: SearchData, expected_count: int) -> None:
        super().__init__(sdata.penalty + extra_penalty)
        self.countries = sdata.countries
        self.postcodes = sdata.postcodes
        self.housenumbers = sdata.housenumbers
        self.qualifiers = sdata.qualifiers
        self.lookups = sdata.lookups
        self.rankings = sdata.rankings
        self.expected_count = expected_count


    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        t = conn.t.placex
        tsearch = conn.t.search_name

        sql: SaLambdaSelect = sa.lambda_stmt(lambda:
                  sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                            t.c.class_, t.c.type,
                            t.c.address, t.c.extratags, t.c.admin_level,
                            t.c.housenumber, t.c.postcode, t.c.country_code,
                            t.c.wikipedia,
                            t.c.parent_place_id, t.c.rank_address, t.c.rank_search,
                            t.c.centroid,
                            t.c.geometry.ST_Expand(0).label('bbox'))
                   .where(t.c.place_id == tsearch.c.place_id))


        if details.geometry_output:
            sql = _add_geometry_columns(sql, t.c.geometry, details)

        penalty: SaExpression = sa.literal(self.penalty)
        for ranking in self.rankings:
            penalty += ranking.sql_penalty(tsearch)

        for lookup in self.lookups:
            sql = sql.where(lookup.sql_condition(tsearch))

        if self.countries:
            sql = sql.where(tsearch.c.country_code.in_(self.countries.values))

        if self.postcodes:
            # if a postcode is given, don't search for state or country level objects
            sql = sql.where(tsearch.c.address_rank > 9)
            tpc = conn.t.postcode
            pcs = self.postcodes.values
            if self.expected_count > 1000:
                # Many results expected. Restrict by postcode.
                sql = sql.where(sa.select(tpc.c.postcode)
                                  .where(tpc.c.postcode.in_(pcs))
                                  .where(tsearch.c.centroid.ST_DWithin(tpc.c.geometry, 0.12))
                                  .exists())

            # Less results, only have a preference for close postcodes
            pc_near = sa.select(sa.func.min(tpc.c.geometry.ST_Distance(tsearch.c.centroid)))\
                      .where(tpc.c.postcode.in_(pcs))\
                      .scalar_subquery()
            penalty += sa.case((t.c.postcode.in_(pcs), 0.0),
                               else_=sa.func.coalesce(pc_near, 2.0))

        if details.viewbox is not None:
            if details.bounded_viewbox:
                if details.viewbox.area < 0.2:
                    sql = sql.where(tsearch.c.centroid.intersects(VIEWBOX_PARAM))
                else:
                    sql = sql.where(tsearch.c.centroid.ST_Intersects_no_index(VIEWBOX_PARAM))
            elif self.expected_count >= 10000:
                if details.viewbox.area < 0.5:
                    sql = sql.where(tsearch.c.centroid.intersects(VIEWBOX2_PARAM))
                else:
                    sql = sql.where(tsearch.c.centroid.ST_Intersects_no_index(VIEWBOX2_PARAM))
            else:
                penalty += sa.case((t.c.geometry.intersects(VIEWBOX_PARAM), 0.0),
                                   (t.c.geometry.intersects(VIEWBOX2_PARAM), 0.5),
                                   else_=1.0)

        if details.near is not None:
            if details.near_radius is not None:
                if details.near_radius < 0.1:
                    sql = sql.where(tsearch.c.centroid.ST_DWithin(NEAR_PARAM, NEAR_RADIUS_PARAM))
                else:
                    sql = sql.where(tsearch.c.centroid.ST_DWithin_no_index(NEAR_PARAM,
                                                                           NEAR_RADIUS_PARAM))
            sql = sql.add_columns((-tsearch.c.centroid.ST_Distance(NEAR_PARAM))
                                      .label('importance'))
            sql = sql.order_by(sa.desc(sa.text('importance')))
        else:
            if self.expected_count < 10000\
               or (details.viewbox is not None and details.viewbox.area < 0.5):
                sql = sql.order_by(
                        penalty - sa.case((tsearch.c.importance > 0, tsearch.c.importance),
                                    else_=0.75001-(sa.cast(tsearch.c.search_rank, sa.Float())/40)))
            sql = sql.add_columns(t.c.importance)


        sql = sql.add_columns(penalty.label('accuracy'))

        if self.expected_count < 10000:
            sql = sql.order_by(sa.text('accuracy'))

        if self.housenumbers:
            hnr_regexp = f"\\m({'|'.join(self.housenumbers.values)})\\M"
            sql = sql.where(tsearch.c.address_rank.between(16, 30))\
                     .where(sa.or_(tsearch.c.address_rank < 30,
                                   t.c.housenumber.op('~*')(hnr_regexp)))

            # Cross check for housenumbers, need to do that on a rather large
            # set. Worst case there are 40.000 main streets in OSM.
            inner = sql.limit(10000).subquery()

            # Housenumbers from placex
            thnr = conn.t.placex.alias('hnr')
            pid_list = array_agg(thnr.c.place_id) # type: ignore[no-untyped-call]
            place_sql = sa.select(pid_list)\
                          .where(thnr.c.parent_place_id == inner.c.place_id)\
                          .where(thnr.c.housenumber.op('~*')(hnr_regexp))\
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
                    .order_by(sa.case((unsort.c.placex_hnr != None, 1),
                                      (unsort.c.interpol_hnr != None, 2),
                                      (unsort.c.tiger_hnr != None, 3),
                                      else_=4),
                              unsort.c.accuracy)
        else:
            sql = sql.where(t.c.linked_place_id == None)\
                     .where(t.c.indexed_status == 0)
            if self.qualifiers:
                sql = sql.where(self.qualifiers.sql_restrict(t))
            if details.excluded:
                sql = sql.where(_exclude_places(tsearch))
            if details.min_rank > 0:
                sql = sql.where(sa.or_(tsearch.c.address_rank >= MIN_RANK_PARAM,
                                       tsearch.c.search_rank >= MIN_RANK_PARAM))
            if details.max_rank < 30:
                sql = sql.where(sa.or_(tsearch.c.address_rank <= MAX_RANK_PARAM,
                                       tsearch.c.search_rank <= MAX_RANK_PARAM))
            if details.layers is not None:
                sql = sql.where(_filter_by_layer(t, details.layers))

        sql = sql.limit(LIMIT_PARAM)

        results = nres.SearchResults()
        for row in await conn.execute(sql, _details_to_bind_params(details)):
            result = nres.create_from_placex_row(row, nres.SearchResult)
            assert result
            result.bbox = Bbox.from_wkb(row.bbox)
            result.accuracy = row.accuracy
            if not details.excluded or not result.place_id in details.excluded:
                results.append(result)

            if self.housenumbers and row.rank_address < 30:
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

                result.accuracy += 1.0 # penalty for missing housenumber

        return results
