# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of reverse geocoding.
"""
from typing import Optional, List

import sqlalchemy as sa
from geoalchemy2 import WKTElement

from nominatim.typing import SaColumn, SaSelect, SaFromClause, SaLabel, SaRow
from nominatim.api.connection import SearchConnection
import nominatim.api.results as nres
from nominatim.api.logging import log
from nominatim.api.types import AnyPoint, DataLayer, LookupDetails, GeometryFormat

# In SQLAlchemy expression which compare with NULL need to be expressed with
# the equal sign.
# pylint: disable=singleton-comparison

def _select_from_placex(t: SaFromClause, wkt: Optional[str] = None) -> SaSelect:
    """ Create a select statement with the columns relevant for reverse
        results.
    """
    if wkt is None:
        distance = t.c.distance
    else:
        distance = t.c.geometry.ST_Distance(wkt)

    return sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                     t.c.class_, t.c.type,
                     t.c.address, t.c.extratags,
                     t.c.housenumber, t.c.postcode, t.c.country_code,
                     t.c.importance, t.c.wikipedia,
                     t.c.parent_place_id, t.c.rank_address, t.c.rank_search,
                     t.c.centroid,
                     distance.label('distance'),
                     t.c.geometry.ST_Expand(0).label('bbox'))


def _interpolated_housenumber(table: SaFromClause) -> SaLabel:
    return sa.cast(table.c.startnumber
                    + sa.func.round(((table.c.endnumber - table.c.startnumber) * table.c.position)
                                    / table.c.step) * table.c.step,
                   sa.Integer).label('housenumber')


def _is_address_point(table: SaFromClause) -> SaColumn:
    return sa.and_(table.c.rank_address == 30,
                   sa.or_(table.c.housenumber != None,
                          table.c.name.has_key('housename')))

def _get_closest(*rows: Optional[SaRow]) -> Optional[SaRow]:
    return min(rows, key=lambda row: 1000 if row is None else row.distance)

class ReverseGeocoder:
    """ Class implementing the logic for looking up a place from a
        coordinate.
    """

    def __init__(self, conn: SearchConnection, max_rank: int, layer: DataLayer,
                 details: LookupDetails) -> None:
        self.conn = conn
        self.max_rank = max_rank
        self.layer = layer
        self.details = details


    def _add_geometry_columns(self, sql: SaSelect, col: SaColumn) -> SaSelect:
        if not self.details.geometry_output:
            return sql

        out = []

        if self.details.geometry_simplification > 0.0:
            col = col.ST_SimplifyPreserveTopology(self.details.geometry_simplification)

        if self.details.geometry_output & GeometryFormat.GEOJSON:
            out.append(col.ST_AsGeoJSON().label('geometry_geojson'))
        if self.details.geometry_output & GeometryFormat.TEXT:
            out.append(col.ST_AsText().label('geometry_text'))
        if self.details.geometry_output & GeometryFormat.KML:
            out.append(col.ST_AsKML().label('geometry_kml'))
        if self.details.geometry_output & GeometryFormat.SVG:
            out.append(col.ST_AsSVG().label('geometry_svg'))

        return sql.add_columns(*out)


    def _filter_by_layer(self, table: SaFromClause) -> SaColumn:
        if self.layer & DataLayer.MANMADE:
            exclude = []
            if not self.layer & DataLayer.RAILWAY:
                exclude.append('railway')
            if not self.layer & DataLayer.NATURAL:
                exclude.extend(('natural', 'water', 'waterway'))
            return table.c.class_.not_in(tuple(exclude))

        include = []
        if self.layer & DataLayer.RAILWAY:
            include.append('railway')
        if self.layer & DataLayer.NATURAL:
            include.extend(('natural', 'water', 'waterway'))
        return table.c.class_.in_(tuple(include))


    async def _find_closest_street_or_poi(self, wkt: WKTElement,
                                          distance: float) -> Optional[SaRow]:
        """ Look up the closest rank 26+ place in the database, which
            is closer than the given distance.
        """
        t = self.conn.t.placex

        sql = _select_from_placex(t, wkt)\
                .where(t.c.geometry.ST_DWithin(wkt, distance))\
                .where(t.c.indexed_status == 0)\
                .where(t.c.linked_place_id == None)\
                .where(sa.or_(t.c.geometry.ST_GeometryType()
                                          .not_in(('ST_Polygon', 'ST_MultiPolygon')),
                              t.c.centroid.ST_Distance(wkt) < distance))\
                .order_by('distance')\
                .limit(1)

        sql = self._add_geometry_columns(sql, t.c.geometry)

        restrict: List[SaColumn] = []

        if self.layer & DataLayer.ADDRESS:
            restrict.append(sa.and_(t.c.rank_address >= 26,
                                    t.c.rank_address <= min(29, self.max_rank)))
            if self.max_rank == 30:
                restrict.append(_is_address_point(t))
        if self.layer & DataLayer.POI and self.max_rank == 30:
            restrict.append(sa.and_(t.c.rank_search == 30,
                                    t.c.class_.not_in(('place', 'building')),
                                    t.c.geometry.ST_GeometryType() != 'ST_LineString'))
        if self.layer & (DataLayer.RAILWAY | DataLayer.MANMADE | DataLayer.NATURAL):
            restrict.append(sa.and_(t.c.rank_search.between(26, self.max_rank),
                                    t.c.rank_address == 0,
                                    self._filter_by_layer(t)))

        if not restrict:
            return None

        return (await self.conn.execute(sql.where(sa.or_(*restrict)))).one_or_none()


    async def _find_housenumber_for_street(self, parent_place_id: int,
                                           wkt: WKTElement) -> Optional[SaRow]:
        t = self.conn.t.placex

        sql = _select_from_placex(t, wkt)\
                .where(t.c.geometry.ST_DWithin(wkt, 0.001))\
                .where(t.c.parent_place_id == parent_place_id)\
                .where(_is_address_point(t))\
                .where(t.c.indexed_status == 0)\
                .where(t.c.linked_place_id == None)\
                .order_by('distance')\
                .limit(1)

        sql = self._add_geometry_columns(sql, t.c.geometry)

        return (await self.conn.execute(sql)).one_or_none()


    async def _find_interpolation_for_street(self, parent_place_id: Optional[int],
                                             wkt: WKTElement,
                                             distance: float) -> Optional[SaRow]:
        t = self.conn.t.osmline

        sql = sa.select(t,
                        t.c.linegeo.ST_Distance(wkt).label('distance'),
                        t.c.linegeo.ST_LineLocatePoint(wkt).label('position'))\
                .where(t.c.linegeo.ST_DWithin(wkt, distance))\
                .order_by('distance')\
                .limit(1)

        if parent_place_id is not None:
            sql = sql.where(t.c.parent_place_id == parent_place_id)

        inner = sql.subquery()

        sql = sa.select(inner.c.place_id, inner.c.osm_id,
                        inner.c.parent_place_id, inner.c.address,
                        _interpolated_housenumber(inner),
                        inner.c.postcode, inner.c.country_code,
                        inner.c.linegeo.ST_LineInterpolatePoint(inner.c.position).label('centroid'),
                        inner.c.distance)

        if self.details.geometry_output:
            sub = sql.subquery()
            sql = self._add_geometry_columns(sql, sub.c.centroid)

        return (await self.conn.execute(sql)).one_or_none()


    async def _find_tiger_number_for_street(self, parent_place_id: int,
                                            wkt: WKTElement) -> Optional[SaRow]:
        t = self.conn.t.tiger

        inner = sa.select(t,
                          t.c.linegeo.ST_Distance(wkt).label('distance'),
                          sa.func.ST_LineLocatePoint(t.c.linegeo, wkt).label('position'))\
                  .where(t.c.linegeo.ST_DWithin(wkt, 0.001))\
                  .where(t.c.parent_place_id == parent_place_id)\
                  .order_by('distance')\
                  .limit(1)\
                  .subquery()

        sql = sa.select(inner.c.place_id,
                        inner.c.parent_place_id,
                        _interpolated_housenumber(inner),
                        inner.c.postcode,
                        inner.c.linegeo.ST_LineInterpolatePoint(inner.c.position).label('centroid'),
                        inner.c.distance)

        if self.details.geometry_output:
            sub = sql.subquery()
            sql = self._add_geometry_columns(sql, sub.c.centroid)

        return (await self.conn.execute(sql)).one_or_none()


    async def lookup_street_poi(self, wkt: WKTElement) -> Optional[nres.ReverseResult]:
        """ Find a street or POI/address for the given WKT point.
        """
        log().section('Reverse lookup on street/address level')
        result = None
        distance = 0.006
        parent_place_id = None

        row = await self._find_closest_street_or_poi(wkt, distance)
        log().var_dump('Result (street/building)', row)

        # If the closest result was a street, but an address was requested,
        # check for a housenumber nearby which is part of the street.
        if row is not None:
            if self.max_rank > 27 \
               and self.layer & DataLayer.ADDRESS \
               and row.rank_address <= 27:
                distance = 0.001
                parent_place_id = row.place_id
                log().comment('Find housenumber for street')
                addr_row = await self._find_housenumber_for_street(parent_place_id, wkt)
                log().var_dump('Result (street housenumber)', addr_row)

                if addr_row is not None:
                    row = addr_row
                    distance = addr_row.distance
                elif row.country_code == 'us' and parent_place_id is not None:
                    log().comment('Find TIGER housenumber for street')
                    addr_row = await self._find_tiger_number_for_street(parent_place_id, wkt)
                    log().var_dump('Result (street Tiger housenumber)', addr_row)

                    if addr_row is not None:
                        result = nres.create_from_tiger_row(addr_row, nres.ReverseResult)
            else:
                distance = row.distance

        # Check for an interpolation that is either closer than our result
        # or belongs to a close street found.
        if self.max_rank > 27 and self.layer & DataLayer.ADDRESS:
            log().comment('Find interpolation for street')
            addr_row = await self._find_interpolation_for_street(parent_place_id,
                                                                 wkt, distance)
            log().var_dump('Result (street interpolation)', addr_row)
            if addr_row is not None:
                result = nres.create_from_osmline_row(addr_row, nres.ReverseResult)

        return result or nres.create_from_placex_row(row, nres.ReverseResult)


    async def _lookup_area_address(self, wkt: WKTElement) -> Optional[SaRow]:
        """ Lookup large addressable areas for the given WKT point.
        """
        log().comment('Reverse lookup by larger address area features')
        t = self.conn.t.placex

        # The inner SQL brings results in the right order, so that
        # later only a minimum of results needs to be checked with ST_Contains.
        inner = sa.select(t, sa.literal(0.0).label('distance'))\
                  .where(t.c.rank_search.between(5, self.max_rank))\
                  .where(t.c.rank_address.between(5, 25))\
                  .where(t.c.geometry.ST_GeometryType().in_(('ST_Polygon', 'ST_MultiPolygon')))\
                  .where(t.c.geometry.intersects(wkt))\
                  .where(t.c.name != None)\
                  .where(t.c.indexed_status == 0)\
                  .where(t.c.linked_place_id == None)\
                  .where(t.c.type != 'postcode')\
                  .order_by(sa.desc(t.c.rank_search))\
                  .limit(50)\
                  .subquery()

        sql = _select_from_placex(inner)\
                  .where(inner.c.geometry.ST_Contains(wkt))\
                  .order_by(sa.desc(inner.c.rank_search))\
                  .limit(1)

        sql = self._add_geometry_columns(sql, inner.c.geometry)

        address_row = (await self.conn.execute(sql)).one_or_none()
        log().var_dump('Result (area)', address_row)

        if address_row is not None and address_row.rank_search < self.max_rank:
            log().comment('Search for better matching place nodes inside the area')
            inner = sa.select(t,
                              t.c.geometry.ST_Distance(wkt).label('distance'))\
                      .where(t.c.osm_type == 'N')\
                      .where(t.c.rank_search > address_row.rank_search)\
                      .where(t.c.rank_search <= self.max_rank)\
                      .where(t.c.rank_address.between(5, 25))\
                      .where(t.c.name != None)\
                      .where(t.c.indexed_status == 0)\
                      .where(t.c.linked_place_id == None)\
                      .where(t.c.type != 'postcode')\
                      .where(t.c.geometry
                                .ST_Buffer(sa.func.reverse_place_diameter(t.c.rank_search))
                                .intersects(wkt))\
                      .order_by(sa.desc(t.c.rank_search))\
                      .limit(50)\
                      .subquery()

            touter = self.conn.t.placex.alias('outer')
            sql = _select_from_placex(inner)\
                  .join(touter, touter.c.geometry.ST_Contains(inner.c.geometry))\
                  .where(touter.c.place_id == address_row.place_id)\
                  .where(inner.c.distance < sa.func.reverse_place_diameter(inner.c.rank_search))\
                  .order_by(sa.desc(inner.c.rank_search), inner.c.distance)\
                  .limit(1)

            sql = self._add_geometry_columns(sql, inner.c.geometry)

            place_address_row = (await self.conn.execute(sql)).one_or_none()
            log().var_dump('Result (place node)', place_address_row)

            if place_address_row is not None:
                return place_address_row

        return address_row


    async def _lookup_area_others(self, wkt: WKTElement) -> Optional[SaRow]:
        t = self.conn.t.placex

        inner = sa.select(t, t.c.geometry.ST_Distance(wkt).label('distance'))\
                  .where(t.c.rank_address == 0)\
                  .where(t.c.rank_search.between(5, self.max_rank))\
                  .where(t.c.name != None)\
                  .where(t.c.indexed_status == 0)\
                  .where(t.c.linked_place_id == None)\
                  .where(self._filter_by_layer(t))\
                  .where(t.c.geometry
                                .ST_Buffer(sa.func.reverse_place_diameter(t.c.rank_search))
                                .intersects(wkt))\
                  .order_by(sa.desc(t.c.rank_search))\
                  .limit(50)\
                  .subquery()

        sql = _select_from_placex(inner)\
                  .where(sa.or_(inner.c.geometry.ST_GeometryType()
                                                .not_in(('ST_Polygon', 'ST_MultiPolygon')),
                                inner.c.geometry.ST_Contains(wkt)))\
                  .order_by(sa.desc(inner.c.rank_search), inner.c.distance)\
                  .limit(1)

        sql = self._add_geometry_columns(sql, inner.c.geometry)

        row = (await self.conn.execute(sql)).one_or_none()
        log().var_dump('Result (non-address feature)', row)

        return row


    async def lookup_area(self, wkt: WKTElement) -> Optional[nres.ReverseResult]:
        """ Lookup large areas for the given WKT point.
        """
        log().section('Reverse lookup by larger area features')

        if self.layer & DataLayer.ADDRESS:
            address_row = await self._lookup_area_address(wkt)
        else:
            address_row = None

        if self.layer & (~DataLayer.ADDRESS & ~DataLayer.POI):
            other_row = await self._lookup_area_others(wkt)
        else:
            other_row = None

        return nres.create_from_placex_row(_get_closest(address_row, other_row), nres.ReverseResult)


    async def lookup_country(self, wkt: WKTElement) -> Optional[nres.ReverseResult]:
        """ Lookup the country for the given WKT point.
        """
        log().section('Reverse lookup by country code')
        t = self.conn.t.country_grid
        sql = sa.select(t.c.country_code).distinct()\
                .where(t.c.geometry.ST_Contains(wkt))

        ccodes = tuple((r[0] for r in await self.conn.execute(sql)))
        log().var_dump('Country codes', ccodes)

        if not ccodes:
            return None

        t = self.conn.t.placex
        if self.max_rank > 4:
            log().comment('Search for place nodes in country')

            inner = sa.select(t,
                              t.c.geometry.ST_Distance(wkt).label('distance'))\
                      .where(t.c.osm_type == 'N')\
                      .where(t.c.rank_search > 4)\
                      .where(t.c.rank_search <= self.max_rank)\
                      .where(t.c.rank_address.between(5, 25))\
                      .where(t.c.name != None)\
                      .where(t.c.indexed_status == 0)\
                      .where(t.c.linked_place_id == None)\
                      .where(t.c.type != 'postcode')\
                      .where(t.c.country_code.in_(ccodes))\
                      .where(t.c.geometry
                                .ST_Buffer(sa.func.reverse_place_diameter(t.c.rank_search))
                                .intersects(wkt))\
                      .order_by(sa.desc(t.c.rank_search))\
                      .limit(50)\
                      .subquery()

            sql = _select_from_placex(inner)\
                  .where(inner.c.distance < sa.func.reverse_place_diameter(inner.c.rank_search))\
                  .order_by(sa.desc(inner.c.rank_search), inner.c.distance)\
                  .limit(1)

            sql = self._add_geometry_columns(sql, inner.c.geometry)

            address_row = (await self.conn.execute(sql)).one_or_none()
            log().var_dump('Result (addressable place node)', address_row)
        else:
            address_row = None

        if address_row is None:
            # Still nothing, then return a country with the appropriate country code.
            sql = _select_from_placex(t, wkt)\
                      .where(t.c.country_code.in_(ccodes))\
                      .where(t.c.rank_address == 4)\
                      .where(t.c.rank_search == 4)\
                      .where(t.c.linked_place_id == None)\
                      .order_by('distance')

            sql = self._add_geometry_columns(sql, t.c.geometry)

            address_row = (await self.conn.execute(sql)).one_or_none()

        return nres.create_from_placex_row(address_row, nres.ReverseResult)


    async def lookup(self, coord: AnyPoint) -> Optional[nres.ReverseResult]:
        """ Look up a single coordinate. Returns the place information,
            if a place was found near the coordinates or None otherwise.
        """
        log().function('reverse_lookup',
                       coord=coord, max_rank=self.max_rank,
                       layer=self.layer, details=self.details)


        wkt = WKTElement(f'POINT({coord[0]} {coord[1]})', srid=4326)

        result: Optional[nres.ReverseResult] = None

        if self.max_rank >= 26:
            result = await self.lookup_street_poi(wkt)
        if result is None and self.max_rank > 4:
            result = await self.lookup_area(wkt)
        if result is None and self.layer & DataLayer.ADDRESS:
            result = await self.lookup_country(wkt)
        if result is not None:
            await nres.add_result_details(self.conn, result, self.details)

        return result
