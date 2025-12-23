# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of place lookup by ID (doing many places at once).
"""
from typing import Optional, Callable, Type, Iterable, Tuple, Union
from dataclasses import dataclass
import datetime as dt

import sqlalchemy as sa

from .typing import SaColumn, SaRow, SaSelect
from .connection import SearchConnection
from .logging import log
from . import types as ntyp
from . import results as nres

RowFunc = Callable[[SaRow, Type[nres.BaseResultT]], nres.BaseResultT]

GEOMETRY_TYPE_MAP = {
    'POINT': 'ST_Point',
    'MULTIPOINT': 'ST_MultiPoint',
    'LINESTRING': 'ST_LineString',
    'MULTILINESTRING': 'ST_MultiLineString',
    'POLYGON': 'ST_Polygon',
    'MULTIPOLYGON': 'ST_MultiPolygon',
    'GEOMETRYCOLLECTION': 'ST_GeometryCollection'
}


@dataclass
class LookupTuple:
    """ Data class saving the SQL result for a single lookup.
    """
    pid: ntyp.PlaceRef
    result: Optional[nres.SearchResult] = None


class LookupCollector:
    """ Result collector for the simple lookup.

        Allows for lookup of multiple places simultaneously.
    """

    def __init__(self, places: Iterable[ntyp.PlaceRef],
                 details: ntyp.LookupDetails) -> None:
        self.details = details
        self.lookups = [LookupTuple(p) for p in places]

    def get_results(self) -> nres.SearchResults:
        """ Return the list of results available.
        """
        return nres.SearchResults(p.result for p in self.lookups if p.result is not None)

    async def add_rows_from_sql(self, conn: SearchConnection, sql: SaSelect,
                                col: SaColumn, row_func: RowFunc[nres.SearchResult]) -> bool:
        if self.details.geometry_output:
            if self.details.geometry_simplification > 0.0:
                col = sa.func.ST_SimplifyPreserveTopology(
                    col, self.details.geometry_simplification)

            if self.details.geometry_output & ntyp.GeometryFormat.GEOJSON:
                sql = sql.add_columns(sa.func.ST_AsGeoJSON(col, 7).label('geometry_geojson'))
            if self.details.geometry_output & ntyp.GeometryFormat.TEXT:
                sql = sql.add_columns(sa.func.ST_AsText(col).label('geometry_text'))
            if self.details.geometry_output & ntyp.GeometryFormat.KML:
                sql = sql.add_columns(sa.func.ST_AsKML(col, 7).label('geometry_kml'))
            if self.details.geometry_output & ntyp.GeometryFormat.SVG:
                sql = sql.add_columns(sa.func.ST_AsSVG(col, 0, 7).label('geometry_svg'))

        for row in await conn.execute(sql):
            result = row_func(row, nres.SearchResult)
            if hasattr(row, 'bbox'):
                result.bbox = ntyp.Bbox.from_wkb(row.bbox)

            if self.lookups[row._idx].result is None:
                self.lookups[row._idx].result = result

        return all(p.result is not None for p in self.lookups)

    def enumerate_free_place_ids(self) -> Iterable[Tuple[int, ntyp.PlaceID]]:
        return ((i, p.pid) for i, p in enumerate(self.lookups)
                if p.result is None and isinstance(p.pid, ntyp.PlaceID))

    def enumerate_free_osm_ids(self) -> Iterable[Tuple[int, ntyp.OsmID]]:
        return ((i, p.pid) for i, p in enumerate(self.lookups)
                if p.result is None and isinstance(p.pid, ntyp.OsmID))


class DetailedCollector:
    """ Result collector for detailed lookup.

        Only one place at the time may be looked up.
    """

    def __init__(self, place: ntyp.PlaceRef, with_geometry: bool) -> None:
        self.with_geometry = with_geometry
        self.place = place
        self.result: Optional[nres.DetailedResult] = None

    async def add_rows_from_sql(self, conn: SearchConnection, sql: SaSelect,
                                col: SaColumn, row_func: RowFunc[nres.DetailedResult]) -> bool:
        if self.with_geometry:
            sql = sql.add_columns(
                sa.func.ST_AsGeoJSON(
                    sa.case((sa.func.ST_NPoints(col) > 5000,
                             sa.func.ST_SimplifyPreserveTopology(col, 0.0001)),
                            else_=col), 7).label('geometry_geojson'))
        else:
            sql = sql.add_columns(sa.func.ST_GeometryType(col).label('geometry_type'))

        for row in await conn.execute(sql):
            self.result = row_func(row, nres.DetailedResult)
            # add missing details
            if 'type' in self.result.geometry:
                self.result.geometry['type'] = \
                    GEOMETRY_TYPE_MAP.get(self.result.geometry['type'],
                                          self.result.geometry['type'])
            indexed_date = getattr(row, 'indexed_date', None)
            if indexed_date is not None:
                self.result.indexed_date = indexed_date.replace(tzinfo=dt.timezone.utc)

            return True

        # Nothing found.
        return False

    def enumerate_free_place_ids(self) -> Iterable[Tuple[int, ntyp.PlaceID]]:
        if self.result is None and isinstance(self.place, ntyp.PlaceID):
            return [(0, self.place)]
        return []

    def enumerate_free_osm_ids(self) -> Iterable[Tuple[int, ntyp.OsmID]]:
        if self.result is None and isinstance(self.place, ntyp.OsmID):
            return [(0, self.place)]
        return []


Collector = Union[LookupCollector, DetailedCollector]


async def get_detailed_place(conn: SearchConnection, place: ntyp.PlaceRef,
                             details: ntyp.LookupDetails) -> Optional[nres.DetailedResult]:
    """ Retrieve a place with additional details from the database.
    """
    log().function('get_detailed_place', place=place, details=details)

    if details.geometry_output and details.geometry_output != ntyp.GeometryFormat.GEOJSON:
        raise ValueError("lookup only supports geojosn polygon output.")

    collector = DetailedCollector(place,
                                  bool(details.geometry_output & ntyp.GeometryFormat.GEOJSON))

    for func in (find_in_placex, find_in_osmline, find_in_postcode, find_in_tiger):
        if await func(conn, collector):
            break

    if collector.result is not None:
        await nres.add_result_details(conn, [collector.result], details)

    return collector.result


async def get_places(conn: SearchConnection, places: Iterable[ntyp.PlaceRef],
                     details: ntyp.LookupDetails) -> nres.SearchResults:
    """ Retrieve a list of places as simple search results from the
        database.
    """
    log().function('get_places', places=places, details=details)

    collector = LookupCollector(places, details)

    for func in (find_in_placex, find_in_osmline, find_in_postcode, find_in_tiger):
        if await func(conn, collector):
            break

    results = collector.get_results()
    await nres.add_result_details(conn, results, details)

    return results


async def find_in_placex(conn: SearchConnection, collector: Collector) -> bool:
    """ Search for the given places in the main placex table.
    """
    log().section("Find in placex table")
    t = conn.t.placex
    sql = sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                    t.c.class_, t.c.type, t.c.admin_level,
                    t.c.address, t.c.extratags,
                    t.c.housenumber, t.c.postcode, t.c.country_code,
                    t.c.importance, t.c.wikipedia, t.c.indexed_date,
                    t.c.parent_place_id, t.c.rank_address, t.c.rank_search,
                    t.c.linked_place_id,
                    t.c.geometry.ST_Expand(0).label('bbox'),
                    t.c.centroid)

    for osm_type in ('N', 'W', 'R'):
        osm_ids = [{'i': i, 'oi': p.osm_id, 'oc': p.osm_class or ''}
                   for i, p in collector.enumerate_free_osm_ids()
                   if p.osm_type == osm_type]

        if osm_ids:
            oid_tab = sa.func.JsonArrayEach(sa.type_coerce(osm_ids, sa.JSON))\
                        .table_valued(sa.column('value', type_=sa.JSON))
            psql = sql.add_columns(oid_tab.c.value['i'].as_integer().label('_idx'))\
                      .where(t.c.osm_type == osm_type)\
                      .where(t.c.osm_id == oid_tab.c.value['oi'].as_string().cast(sa.BigInteger))\
                      .where(sa.or_(oid_tab.c.value['oc'].as_string() == '',
                                    oid_tab.c.value['oc'].as_string() == t.c.class_))\
                      .order_by(t.c.class_)

            if await collector.add_rows_from_sql(conn, psql, t.c.geometry,
                                                 nres.create_from_placex_row):
                return True

    place_ids = [{'i': i, 'id': p.place_id}
                 for i, p in collector.enumerate_free_place_ids()]

    if place_ids:
        pid_tab = sa.func.JsonArrayEach(sa.type_coerce(place_ids, sa.JSON))\
                    .table_valued(sa.column('value', type_=sa.JSON))
        psql = sql.add_columns(pid_tab.c.value['i'].as_integer().label('_idx'))\
                  .where(t.c.place_id == pid_tab.c.value['id'].as_string().cast(sa.BigInteger))

        return await collector.add_rows_from_sql(conn, psql, t.c.geometry,
                                                 nres.create_from_placex_row)

    return False


async def find_in_osmline(conn: SearchConnection, collector: Collector) -> bool:
    """ Search for the given places in the table for address interpolations.

        Return true when all places have been resolved.
    """
    log().section("Find in interpolation table")
    t = conn.t.osmline
    sql = sa.select(t.c.place_id, t.c.osm_id, t.c.parent_place_id,
                    t.c.indexed_date, t.c.startnumber, t.c.endnumber,
                    t.c.step, t.c.address, t.c.postcode, t.c.country_code,
                    t.c.linegeo.ST_Centroid().label('centroid'))

    osm_ids = [{'i': i, 'oi': p.osm_id, 'oc': p.class_as_housenumber()}
               for i, p in collector.enumerate_free_osm_ids() if p.osm_type == 'W']

    if osm_ids:
        oid_tab = sa.func.JsonArrayEach(sa.type_coerce(osm_ids, sa.JSON))\
                    .table_valued(sa.column('value', type_=sa.JSON))
        psql = sql.add_columns(oid_tab.c.value['i'].as_integer().label('_idx'))\
                  .where(t.c.osm_id == oid_tab.c.value['oi'].as_string().cast(sa.BigInteger))\
                  .order_by(sa.func.greatest(0,
                                             oid_tab.c.value['oc'].as_integer() - t.c.endnumber,
                                             t.c.startnumber - oid_tab.c.value['oc'].as_integer()))

        if await collector.add_rows_from_sql(conn, psql, t.c.linegeo,
                                             nres.create_from_osmline_row):
            return True

    place_ids = [{'i': i, 'id': p.place_id}
                 for i, p in collector.enumerate_free_place_ids()]

    if place_ids:
        pid_tab = sa.func.JsonArrayEach(sa.type_coerce(place_ids, sa.JSON))\
                    .table_valued(sa.column('value', type_=sa.JSON))
        psql = sql.add_columns(pid_tab.c.value['i'].label('_idx'))\
                  .where(t.c.place_id == pid_tab.c.value['id'].as_string().cast(sa.BigInteger))

        return await collector.add_rows_from_sql(conn, psql, t.c.linegeo,
                                                 nres.create_from_osmline_row)

    return False


async def find_in_postcode(conn: SearchConnection, collector: Collector) -> bool:
    """ Search for the given places in the postcode table.

        Return true when all places have been resolved.
    """
    log().section("Find in postcode table")

    place_ids = [{'i': i, 'id': p.place_id}
                 for i, p in collector.enumerate_free_place_ids()]

    if place_ids:
        pid_tab = sa.func.JsonArrayEach(sa.type_coerce(place_ids, sa.JSON))\
                    .table_valued(sa.column('value', type_=sa.JSON))
        t = conn.t.postcode
        sql = sa.select(pid_tab.c.value['i'].as_integer().label('_idx'),
                        t.c.osm_id, t.c.place_id, t.c.parent_place_id,
                        t.c.rank_search,
                        t.c.indexed_date, t.c.postcode, t.c.country_code,
                        t.c.centroid)\
                .where(t.c.place_id == pid_tab.c.value['id'].as_string().cast(sa.BigInteger))

        if await collector.add_rows_from_sql(conn, sql, t.c.geometry,
                                             nres.create_from_postcode_row):
            return True

    osm_ids = [{'i': i, 'oi': p.osm_id}
               for i, p in collector.enumerate_free_osm_ids() if p.osm_type == 'R']

    if osm_ids:
        pid_tab = sa.func.JsonArrayEach(sa.type_coerce(osm_ids, sa.JSON))\
                    .table_valued(sa.column('value', type_=sa.JSON))
        t = conn.t.postcode
        sql = sa.select(pid_tab.c.value['i'].as_integer().label('_idx'),
                        t.c.osm_id, t.c.place_id, t.c.parent_place_id,
                        t.c.rank_search,
                        t.c.indexed_date, t.c.postcode, t.c.country_code,
                        t.c.centroid)\
                .where(t.c.osm_id == pid_tab.c.value['oi'].as_string().cast(sa.BigInteger))

        return await collector.add_rows_from_sql(conn, sql, t.c.geometry,
                                                 nres.create_from_postcode_row)

    return False


async def find_in_tiger(conn: SearchConnection, collector: Collector) -> bool:
    """ Search for the given places in the TIGER address table.

        Return true when all places have been resolved.
    """
    log().section("Find in tiger table")

    place_ids = [{'i': i, 'id': p.place_id}
                 for i, p in collector.enumerate_free_place_ids()]

    if place_ids:
        pid_tab = sa.func.JsonArrayEach(sa.type_coerce(place_ids, sa.JSON))\
                    .table_valued(sa.column('value', type_=sa.JSON))
        t = conn.t.tiger
        parent = conn.t.placex
        sql = sa.select(pid_tab.c.value['i'].as_integer().label('_idx'),
                        t.c.place_id, t.c.parent_place_id,
                        parent.c.osm_type, parent.c.osm_id,
                        t.c.startnumber, t.c.endnumber, t.c.step,
                        t.c.postcode,
                        t.c.linegeo.ST_Centroid().label('centroid'))\
                .join(parent, t.c.parent_place_id == parent.c.place_id, isouter=True)\
                .where(t.c.place_id == pid_tab.c.value['id'].as_string().cast(sa.BigInteger))

        return await collector.add_rows_from_sql(conn, sql, t.c.linegeo,
                                                 nres.create_from_tiger_row)

    return False
