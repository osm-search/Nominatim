# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of reverse geocoding.
"""
from typing import Optional, List, Callable, Type, Tuple, Dict, Any, cast, Union
import functools

import sqlalchemy as sa

from nominatim.typing import SaColumn, SaSelect, SaFromClause, SaLabel, SaRow,\
                             SaBind, SaLambdaSelect
from nominatim.api.connection import SearchConnection
import nominatim.api.results as nres
from nominatim.api.logging import log
from nominatim.api.types import AnyPoint, DataLayer, ReverseDetails, GeometryFormat, Bbox
from nominatim.db.sqlalchemy_types import Geometry

# In SQLAlchemy expression which compare with NULL need to be expressed with
# the equal sign.
# pylint: disable=singleton-comparison

RowFunc = Callable[[Optional[SaRow], Type[nres.ReverseResult]], Optional[nres.ReverseResult]]

WKT_PARAM: SaBind = sa.bindparam('wkt', type_=Geometry)
MAX_RANK_PARAM: SaBind = sa.bindparam('max_rank')

def no_index(expr: SaColumn) -> SaColumn:
    """ Wrap the given expression, so that the query planner will
        refrain from using the expression for index lookup.
    """
    return sa.func.coalesce(sa.null(), expr) # pylint: disable=not-callable


def _select_from_placex(t: SaFromClause, use_wkt: bool = True) -> SaSelect:
    """ Create a select statement with the columns relevant for reverse
        results.
    """
    if not use_wkt:
        distance = t.c.distance
        centroid = t.c.centroid
    else:
        distance = t.c.geometry.ST_Distance(WKT_PARAM)
        centroid = sa.case((t.c.geometry.is_line_like(), t.c.geometry.ST_ClosestPoint(WKT_PARAM)),
                           else_=t.c.centroid).label('centroid')


    return sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                     t.c.class_, t.c.type,
                     t.c.address, t.c.extratags,
                     t.c.housenumber, t.c.postcode, t.c.country_code,
                     t.c.importance, t.c.wikipedia,
                     t.c.parent_place_id, t.c.rank_address, t.c.rank_search,
                     centroid,
                     t.c.linked_place_id, t.c.admin_level,
                     distance.label('distance'),
                     t.c.geometry.ST_Expand(0).label('bbox'))


def _interpolated_housenumber(table: SaFromClause) -> SaLabel:
    return sa.cast(table.c.startnumber
                    + sa.func.round(((table.c.endnumber - table.c.startnumber) * table.c.position)
                                    / table.c.step) * table.c.step,
                   sa.Integer).label('housenumber')


def _interpolated_position(table: SaFromClause) -> SaLabel:
    fac = sa.cast(table.c.step, sa.Float) / (table.c.endnumber - table.c.startnumber)
    rounded_pos = sa.func.round(table.c.position / fac) * fac
    return sa.case(
             (table.c.endnumber == table.c.startnumber, table.c.linegeo.ST_Centroid()),
              else_=table.c.linegeo.ST_LineInterpolatePoint(rounded_pos)).label('centroid')


def _locate_interpolation(table: SaFromClause) -> SaLabel:
    """ Given a position, locate the closest point on the line.
    """
    return sa.case((table.c.linegeo.is_line_like(),
                    table.c.linegeo.ST_LineLocatePoint(WKT_PARAM)),
                   else_=0).label('position')


def _get_closest(*rows: Optional[SaRow]) -> Optional[SaRow]:
    return min(rows, key=lambda row: 1000 if row is None else row.distance)


class ReverseGeocoder:
    """ Class implementing the logic for looking up a place from a
        coordinate.
    """

    def __init__(self, conn: SearchConnection, params: ReverseDetails,
                 restrict_to_country_areas: bool = False) -> None:
        self.conn = conn
        self.params = params
        self.restrict_to_country_areas = restrict_to_country_areas

        self.bind_params: Dict[str, Any] = {'max_rank': params.max_rank}


    @property
    def max_rank(self) -> int:
        """ Return the maximum configured rank.
        """
        return self.params.max_rank


    def has_geometries(self) -> bool:
        """ Check if any geometries are requested.
        """
        return bool(self.params.geometry_output)


    def layer_enabled(self, *layer: DataLayer) -> bool:
        """ Return true when any of the given layer types are requested.
        """
        return any(self.params.layers & l for l in layer)


    def layer_disabled(self, *layer: DataLayer) -> bool:
        """ Return true when none of the given layer types is requested.
        """
        return not any(self.params.layers & l for l in layer)


    def has_feature_layers(self) -> bool:
        """ Return true if any layer other than ADDRESS or POI is requested.
        """
        return self.layer_enabled(DataLayer.RAILWAY, DataLayer.MANMADE, DataLayer.NATURAL)


    def _add_geometry_columns(self, sql: SaLambdaSelect, col: SaColumn) -> SaSelect:
        out = []

        if self.params.geometry_simplification > 0.0:
            col = sa.func.ST_SimplifyPreserveTopology(col, self.params.geometry_simplification)

        if self.params.geometry_output & GeometryFormat.GEOJSON:
            out.append(sa.func.ST_AsGeoJSON(col, 7).label('geometry_geojson'))
        if self.params.geometry_output & GeometryFormat.TEXT:
            out.append(sa.func.ST_AsText(col).label('geometry_text'))
        if self.params.geometry_output & GeometryFormat.KML:
            out.append(sa.func.ST_AsKML(col, 7).label('geometry_kml'))
        if self.params.geometry_output & GeometryFormat.SVG:
            out.append(sa.func.ST_AsSVG(col, 0, 7).label('geometry_svg'))

        return sql.add_columns(*out)


    def _filter_by_layer(self, table: SaFromClause) -> SaColumn:
        if self.layer_enabled(DataLayer.MANMADE):
            exclude = []
            if self.layer_disabled(DataLayer.RAILWAY):
                exclude.append('railway')
            if self.layer_disabled(DataLayer.NATURAL):
                exclude.extend(('natural', 'water', 'waterway'))
            return table.c.class_.not_in(tuple(exclude))

        include = []
        if self.layer_enabled(DataLayer.RAILWAY):
            include.append('railway')
        if self.layer_enabled(DataLayer.NATURAL):
            include.extend(('natural', 'water', 'waterway'))
        return table.c.class_.in_(tuple(include))


    async def _find_closest_street_or_poi(self, distance: float) -> Optional[SaRow]:
        """ Look up the closest rank 26+ place in the database, which
            is closer than the given distance.
        """
        t = self.conn.t.placex

        # PostgreSQL must not get the distance as a parameter because
        # there is a danger it won't be able to proberly estimate index use
        # when used with prepared statements
        diststr = sa.text(f"{distance}")

        sql: SaLambdaSelect = sa.lambda_stmt(lambda: _select_from_placex(t)
                .where(t.c.geometry.ST_DWithin(WKT_PARAM, diststr))
                .where(t.c.indexed_status == 0)
                .where(t.c.linked_place_id == None)
                .where(sa.or_(sa.not_(t.c.geometry.is_area()),
                              t.c.centroid.ST_Distance(WKT_PARAM) < diststr))
                .order_by('distance')
                .limit(1))

        if self.has_geometries():
            sql = self._add_geometry_columns(sql, t.c.geometry)

        restrict: List[Union[SaColumn, Callable[[], SaColumn]]] = []

        if self.layer_enabled(DataLayer.ADDRESS):
            max_rank = min(29, self.max_rank)
            restrict.append(lambda: no_index(t.c.rank_address).between(26, max_rank))
            if self.max_rank == 30:
                restrict.append(lambda: sa.func.IsAddressPoint(t))
        if self.layer_enabled(DataLayer.POI) and self.max_rank == 30:
            restrict.append(lambda: sa.and_(no_index(t.c.rank_search) == 30,
                                            t.c.class_.not_in(('place', 'building')),
                                            sa.not_(t.c.geometry.is_line_like())))
        if self.has_feature_layers():
            restrict.append(sa.and_(no_index(t.c.rank_search).between(26, MAX_RANK_PARAM),
                                    no_index(t.c.rank_address) == 0,
                                    self._filter_by_layer(t)))

        if not restrict:
            return None

        sql = sql.where(sa.or_(*restrict))

        return (await self.conn.execute(sql, self.bind_params)).one_or_none()


    async def _find_housenumber_for_street(self, parent_place_id: int) -> Optional[SaRow]:
        t = self.conn.t.placex

        sql: SaLambdaSelect = sa.lambda_stmt(lambda: _select_from_placex(t)
                .where(t.c.geometry.ST_DWithin(WKT_PARAM, 0.001))
                .where(t.c.parent_place_id == parent_place_id)
                .where(sa.func.IsAddressPoint(t))
                .where(t.c.indexed_status == 0)
                .where(t.c.linked_place_id == None)
                .order_by('distance')
                .limit(1))

        if self.has_geometries():
            sql = self._add_geometry_columns(sql, t.c.geometry)

        return (await self.conn.execute(sql, self.bind_params)).one_or_none()


    async def _find_interpolation_for_street(self, parent_place_id: Optional[int],
                                             distance: float) -> Optional[SaRow]:
        t = self.conn.t.osmline

        sql: Any = sa.lambda_stmt(lambda:
                   sa.select(t,
                             t.c.linegeo.ST_Distance(WKT_PARAM).label('distance'),
                             _locate_interpolation(t))
                     .where(t.c.linegeo.ST_DWithin(WKT_PARAM, distance))
                     .where(t.c.startnumber != None)
                     .order_by('distance')
                     .limit(1))

        if parent_place_id is not None:
            sql += lambda s: s.where(t.c.parent_place_id == parent_place_id)

        def _wrap_query(base_sql: SaLambdaSelect) -> SaSelect:
            inner = base_sql.subquery('ipol')

            return sa.select(inner.c.place_id, inner.c.osm_id,
                             inner.c.parent_place_id, inner.c.address,
                             _interpolated_housenumber(inner),
                             _interpolated_position(inner),
                             inner.c.postcode, inner.c.country_code,
                             inner.c.distance)

        sql += _wrap_query

        if self.has_geometries():
            sub = sql.subquery('geom')
            sql = self._add_geometry_columns(sa.select(sub), sub.c.centroid)

        return (await self.conn.execute(sql, self.bind_params)).one_or_none()


    async def _find_tiger_number_for_street(self, parent_place_id: int) -> Optional[SaRow]:
        t = self.conn.t.tiger

        def _base_query() -> SaSelect:
            inner = sa.select(t,
                              t.c.linegeo.ST_Distance(WKT_PARAM).label('distance'),
                              _locate_interpolation(t))\
                      .where(t.c.linegeo.ST_DWithin(WKT_PARAM, 0.001))\
                      .where(t.c.parent_place_id == parent_place_id)\
                      .order_by('distance')\
                      .limit(1)\
                      .subquery('tiger')

            return sa.select(inner.c.place_id,
                             inner.c.parent_place_id,
                             _interpolated_housenumber(inner),
                             _interpolated_position(inner),
                             inner.c.postcode,
                             inner.c.distance)

        sql: SaLambdaSelect = sa.lambda_stmt(_base_query)

        if self.has_geometries():
            sub = sql.subquery('geom')
            sql = self._add_geometry_columns(sa.select(sub), sub.c.centroid)

        return (await self.conn.execute(sql, self.bind_params)).one_or_none()


    async def lookup_street_poi(self) -> Tuple[Optional[SaRow], RowFunc]:
        """ Find a street or POI/address for the given WKT point.
        """
        log().section('Reverse lookup on street/address level')
        distance = 0.006
        parent_place_id = None

        row = await self._find_closest_street_or_poi(distance)
        row_func: RowFunc = nres.create_from_placex_row
        log().var_dump('Result (street/building)', row)

        # If the closest result was a street, but an address was requested,
        # check for a housenumber nearby which is part of the street.
        if row is not None:
            if self.max_rank > 27 \
               and self.layer_enabled(DataLayer.ADDRESS) \
               and row.rank_address <= 27:
                distance = 0.001
                parent_place_id = row.place_id
                log().comment('Find housenumber for street')
                addr_row = await self._find_housenumber_for_street(parent_place_id)
                log().var_dump('Result (street housenumber)', addr_row)

                if addr_row is not None:
                    row = addr_row
                    row_func = nres.create_from_placex_row
                    distance = addr_row.distance
                elif row.country_code == 'us' and parent_place_id is not None:
                    log().comment('Find TIGER housenumber for street')
                    addr_row = await self._find_tiger_number_for_street(parent_place_id)
                    log().var_dump('Result (street Tiger housenumber)', addr_row)

                    if addr_row is not None:
                        row_func = cast(RowFunc,
                                        functools.partial(nres.create_from_tiger_row,
                                                          osm_type=row.osm_type,
                                                          osm_id=row.osm_id))
                        row = addr_row
            else:
                distance = row.distance

        # Check for an interpolation that is either closer than our result
        # or belongs to a close street found.
        if self.max_rank > 27 and self.layer_enabled(DataLayer.ADDRESS):
            log().comment('Find interpolation for street')
            addr_row = await self._find_interpolation_for_street(parent_place_id,
                                                                 distance)
            log().var_dump('Result (street interpolation)', addr_row)
            if addr_row is not None:
                row = addr_row
                row_func = nres.create_from_osmline_row

        return row, row_func


    async def _lookup_area_address(self) -> Optional[SaRow]:
        """ Lookup large addressable areas for the given WKT point.
        """
        log().comment('Reverse lookup by larger address area features')
        t = self.conn.t.placex

        def _base_query() -> SaSelect:
            # The inner SQL brings results in the right order, so that
            # later only a minimum of results needs to be checked with ST_Contains.
            inner = sa.select(t, sa.literal(0.0).label('distance'))\
                      .where(t.c.rank_search.between(5, MAX_RANK_PARAM))\
                      .where(t.c.geometry.intersects(WKT_PARAM))\
                      .where(sa.func.PlacexGeometryReverseLookuppolygon())\
                      .order_by(sa.desc(t.c.rank_search))\
                      .limit(50)\
                      .subquery('area')

            return _select_from_placex(inner, False)\
                      .where(inner.c.geometry.ST_Contains(WKT_PARAM))\
                      .order_by(sa.desc(inner.c.rank_search))\
                      .limit(1)

        sql: SaLambdaSelect = sa.lambda_stmt(_base_query)
        if self.has_geometries():
            sql = self._add_geometry_columns(sql, sa.literal_column('area.geometry'))

        address_row = (await self.conn.execute(sql, self.bind_params)).one_or_none()
        log().var_dump('Result (area)', address_row)

        if address_row is not None and address_row.rank_search < self.max_rank:
            log().comment('Search for better matching place nodes inside the area')

            address_rank = address_row.rank_search
            address_id = address_row.place_id

            def _place_inside_area_query() -> SaSelect:
                inner = \
                    sa.select(t,
                              t.c.geometry.ST_Distance(WKT_PARAM).label('distance'))\
                      .where(t.c.rank_search > address_rank)\
                      .where(t.c.rank_search <= MAX_RANK_PARAM)\
                      .where(t.c.indexed_status == 0)\
                      .where(sa.func.IntersectsReverseDistance(t, WKT_PARAM))\
                      .order_by(sa.desc(t.c.rank_search))\
                      .limit(50)\
                      .subquery('places')

                touter = t.alias('outer')
                return _select_from_placex(inner, False)\
                    .join(touter, touter.c.geometry.ST_Contains(inner.c.geometry))\
                    .where(touter.c.place_id == address_id)\
                    .where(sa.func.IsBelowReverseDistance(inner.c.distance, inner.c.rank_search))\
                    .order_by(sa.desc(inner.c.rank_search), inner.c.distance)\
                    .limit(1)

            sql = sa.lambda_stmt(_place_inside_area_query)
            if self.has_geometries():
                sql = self._add_geometry_columns(sql, sa.literal_column('places.geometry'))

            place_address_row = (await self.conn.execute(sql, self.bind_params)).one_or_none()
            log().var_dump('Result (place node)', place_address_row)

            if place_address_row is not None:
                return place_address_row

        return address_row


    async def _lookup_area_others(self) -> Optional[SaRow]:
        t = self.conn.t.placex

        inner = sa.select(t, t.c.geometry.ST_Distance(WKT_PARAM).label('distance'))\
                  .where(t.c.rank_address == 0)\
                  .where(t.c.rank_search.between(5, MAX_RANK_PARAM))\
                  .where(t.c.name != None)\
                  .where(t.c.indexed_status == 0)\
                  .where(t.c.linked_place_id == None)\
                  .where(self._filter_by_layer(t))\
                  .where(t.c.geometry.intersects(sa.func.ST_Expand(WKT_PARAM, 0.007)))\
                  .order_by(sa.desc(t.c.rank_search))\
                  .order_by('distance')\
                  .limit(50)\
                  .subquery()

        sql = _select_from_placex(inner, False)\
                  .where(sa.or_(sa.not_(inner.c.geometry.is_area()),
                                inner.c.geometry.ST_Contains(WKT_PARAM)))\
                  .order_by(sa.desc(inner.c.rank_search), inner.c.distance)\
                  .limit(1)

        if self.has_geometries():
            sql = self._add_geometry_columns(sql, inner.c.geometry)

        row = (await self.conn.execute(sql, self.bind_params)).one_or_none()
        log().var_dump('Result (non-address feature)', row)

        return row


    async def lookup_area(self) -> Optional[SaRow]:
        """ Lookup large areas for the current search.
        """
        log().section('Reverse lookup by larger area features')

        if self.layer_enabled(DataLayer.ADDRESS):
            address_row = await self._lookup_area_address()
        else:
            address_row = None

        if self.has_feature_layers():
            other_row = await self._lookup_area_others()
        else:
            other_row = None

        return _get_closest(address_row, other_row)


    async def lookup_country_codes(self) -> List[str]:
        """ Lookup the country for the current search.
        """
        log().section('Reverse lookup by country code')
        t = self.conn.t.country_grid
        sql = sa.select(t.c.country_code).distinct()\
                .where(t.c.geometry.ST_Contains(WKT_PARAM))

        ccodes = [cast(str, r[0]) for r in await self.conn.execute(sql, self.bind_params)]
        log().var_dump('Country codes', ccodes)
        return ccodes


    async def lookup_country(self, ccodes: List[str]) -> Optional[SaRow]:
        """ Lookup the country for the current search.
        """
        if not ccodes:
            ccodes = await self.lookup_country_codes()

        if not ccodes:
            return None

        t = self.conn.t.placex
        if self.max_rank > 4:
            log().comment('Search for place nodes in country')

            def _base_query() -> SaSelect:
                inner = \
                    sa.select(t,
                              t.c.geometry.ST_Distance(WKT_PARAM).label('distance'))\
                      .where(t.c.rank_search > 4)\
                      .where(t.c.rank_search <= MAX_RANK_PARAM)\
                      .where(t.c.indexed_status == 0)\
                      .where(t.c.country_code.in_(ccodes))\
                      .where(sa.func.IntersectsReverseDistance(t, WKT_PARAM))\
                      .order_by(sa.desc(t.c.rank_search))\
                      .limit(50)\
                      .subquery('area')

                return _select_from_placex(inner, False)\
                    .where(sa.func.IsBelowReverseDistance(inner.c.distance, inner.c.rank_search))\
                    .order_by(sa.desc(inner.c.rank_search), inner.c.distance)\
                    .limit(1)

            sql: SaLambdaSelect = sa.lambda_stmt(_base_query)
            if self.has_geometries():
                sql = self._add_geometry_columns(sql, sa.literal_column('area.geometry'))

            address_row = (await self.conn.execute(sql, self.bind_params)).one_or_none()
            log().var_dump('Result (addressable place node)', address_row)
        else:
            address_row = None

        if address_row is None:
            # Still nothing, then return a country with the appropriate country code.
            sql = sa.lambda_stmt(lambda: _select_from_placex(t)\
                      .where(t.c.country_code.in_(ccodes))\
                      .where(t.c.rank_address == 4)\
                      .where(t.c.rank_search == 4)\
                      .where(t.c.linked_place_id == None)\
                      .order_by('distance')\
                      .limit(1))

            if self.has_geometries():
                sql = self._add_geometry_columns(sql, t.c.geometry)

            address_row = (await self.conn.execute(sql, self.bind_params)).one_or_none()

        return address_row


    async def lookup(self, coord: AnyPoint) -> Optional[nres.ReverseResult]:
        """ Look up a single coordinate. Returns the place information,
            if a place was found near the coordinates or None otherwise.
        """
        log().function('reverse_lookup', coord=coord, params=self.params)


        self.bind_params['wkt'] = f'POINT({coord[0]} {coord[1]})'

        row: Optional[SaRow] = None
        row_func: RowFunc = nres.create_from_placex_row

        if self.max_rank >= 26:
            row, tmp_row_func = await self.lookup_street_poi()
            if row is not None:
                row_func = tmp_row_func

        if row is None:
            if self.restrict_to_country_areas:
                ccodes = await self.lookup_country_codes()
                if not ccodes:
                    return None
            else:
                ccodes = []

            if self.max_rank > 4:
                row = await self.lookup_area()
            if row is None and self.layer_enabled(DataLayer.ADDRESS):
                row = await self.lookup_country(ccodes)

        result = row_func(row, nres.ReverseResult)
        if result is not None:
            assert row is not None
            result.distance = row.distance
            if hasattr(row, 'bbox'):
                result.bbox = Bbox.from_wkb(row.bbox)
            await nres.add_result_details(self.conn, [result], self.params)

        return result
