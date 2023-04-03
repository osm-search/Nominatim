# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of place lookup by ID.
"""
from typing import Optional, Callable, Tuple, Type
import datetime as dt

import sqlalchemy as sa

from nominatim.typing import SaColumn, SaRow, SaSelect
from nominatim.api.connection import SearchConnection
import nominatim.api.types as ntyp
import nominatim.api.results as nres
from nominatim.api.logging import log

RowFunc = Callable[[Optional[SaRow], Type[nres.BaseResultT]], Optional[nres.BaseResultT]]

GeomFunc = Callable[[SaSelect, SaColumn], SaSelect]



async def find_in_placex(conn: SearchConnection, place: ntyp.PlaceRef,
                         add_geometries: GeomFunc) -> Optional[SaRow]:
    """ Search for the given place in the placex table and return the
        base information.
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
                    t.c.centroid)

    if isinstance(place, ntyp.PlaceID):
        sql = sql.where(t.c.place_id == place.place_id)
    elif isinstance(place, ntyp.OsmID):
        sql = sql.where(t.c.osm_type == place.osm_type)\
                 .where(t.c.osm_id == place.osm_id)
        if place.osm_class:
            sql = sql.where(t.c.class_ == place.osm_class)
        else:
            sql = sql.order_by(t.c.class_)
        sql = sql.limit(1)
    else:
        return None

    return (await conn.execute(add_geometries(sql, t.c.geometry))).one_or_none()


async def find_in_osmline(conn: SearchConnection, place: ntyp.PlaceRef,
                          add_geometries: GeomFunc) -> Optional[SaRow]:
    """ Search for the given place in the osmline table and return the
        base information.
    """
    log().section("Find in interpolation table")
    t = conn.t.osmline
    sql = sa.select(t.c.place_id, t.c.osm_id, t.c.parent_place_id,
                    t.c.indexed_date, t.c.startnumber, t.c.endnumber,
                    t.c.step, t.c.address, t.c.postcode, t.c.country_code,
                    t.c.linegeo.ST_Centroid().label('centroid'))

    if isinstance(place, ntyp.PlaceID):
        sql = sql.where(t.c.place_id == place.place_id)
    elif isinstance(place, ntyp.OsmID) and place.osm_type == 'W':
        # There may be multiple interpolations for a single way.
        # If 'class' contains a number, return the one that belongs to that number.
        sql = sql.where(t.c.osm_id == place.osm_id).limit(1)
        if place.osm_class and place.osm_class.isdigit():
            sql = sql.order_by(sa.func.greatest(0,
                                    sa.func.least(int(place.osm_class) - t.c.endnumber),
                                           t.c.startnumber - int(place.osm_class)))
    else:
        return None

    return (await conn.execute(add_geometries(sql, t.c.linegeo))).one_or_none()


async def find_in_tiger(conn: SearchConnection, place: ntyp.PlaceRef,
                        add_geometries: GeomFunc) -> Optional[SaRow]:
    """ Search for the given place in the table of Tiger addresses and return
        the base information. Only lookup by place ID is supported.
    """
    if not isinstance(place, ntyp.PlaceID):
        return None

    log().section("Find in TIGER table")
    t = conn.t.tiger
    parent = conn.t.placex
    sql = sa.select(t.c.place_id, t.c.parent_place_id,
                    parent.c.osm_type, parent.c.osm_id,
                    t.c.startnumber, t.c.endnumber, t.c.step,
                    t.c.postcode,
                    t.c.linegeo.ST_Centroid().label('centroid'))\
            .where(t.c.place_id == place.place_id)\
            .join(parent, t.c.parent_place_id == parent.c.place_id, isouter=True)

    return (await conn.execute(add_geometries(sql, t.c.linegeo))).one_or_none()


async def find_in_postcode(conn: SearchConnection, place: ntyp.PlaceRef,
                           add_geometries: GeomFunc) -> Optional[SaRow]:
    """ Search for the given place in the postcode table and return the
        base information. Only lookup by place ID is supported.
    """
    if not isinstance(place, ntyp.PlaceID):
        return None

    log().section("Find in postcode table")
    t = conn.t.postcode
    sql = sa.select(t.c.place_id, t.c.parent_place_id,
                    t.c.rank_search, t.c.rank_address,
                    t.c.indexed_date, t.c.postcode, t.c.country_code,
                    t.c.geometry.label('centroid')) \
            .where(t.c.place_id == place.place_id)

    return (await conn.execute(add_geometries(sql, t.c.geometry))).one_or_none()


async def find_in_all_tables(conn: SearchConnection, place: ntyp.PlaceRef,
                             add_geometries: GeomFunc
                            ) -> Tuple[Optional[SaRow], RowFunc[nres.BaseResultT]]:
    """ Search for the given place in all data tables
        and return the base information.
    """
    row = await find_in_placex(conn, place, add_geometries)
    log().var_dump('Result (placex)', row)
    if row is not None:
        return row, nres.create_from_placex_row

    row = await find_in_osmline(conn, place, add_geometries)
    log().var_dump('Result (osmline)', row)
    if row is not None:
        return row, nres.create_from_osmline_row

    row = await find_in_postcode(conn, place, add_geometries)
    log().var_dump('Result (postcode)', row)
    if row is not None:
        return row, nres.create_from_postcode_row

    row = await find_in_tiger(conn, place, add_geometries)
    log().var_dump('Result (tiger)', row)
    return row, nres.create_from_tiger_row


async def get_detailed_place(conn: SearchConnection, place: ntyp.PlaceRef,
                             details: ntyp.LookupDetails) -> Optional[nres.DetailedResult]:
    """ Retrieve a place with additional details from the database.
    """
    log().function('get_detailed_place', place=place, details=details)

    if details.geometry_output and details.geometry_output != ntyp.GeometryFormat.GEOJSON:
        raise ValueError("lookup only supports geojosn polygon output.")

    if details.geometry_output & ntyp.GeometryFormat.GEOJSON:
        def _add_geometry(sql: SaSelect, column: SaColumn) -> SaSelect:
            return sql.add_columns(sa.literal_column(f"""
                      ST_AsGeoJSON(CASE WHEN ST_NPoints({column.name}) > 5000
                                   THEN ST_SimplifyPreserveTopology({column.name}, 0.0001)
                                   ELSE {column.name} END)
                       """).label('geometry_geojson'))
    else:
        def _add_geometry(sql: SaSelect, column: SaColumn) -> SaSelect:
            return sql.add_columns(sa.func.ST_GeometryType(column).label('geometry_type'))

    row_func: RowFunc[nres.DetailedResult]
    row, row_func = await find_in_all_tables(conn, place, _add_geometry)

    if row is None:
        return None

    result = row_func(row, nres.DetailedResult)
    assert result is not None

    # add missing details
    assert result is not None
    result.parent_place_id = row.parent_place_id
    result.linked_place_id = getattr(row, 'linked_place_id', None)
    result.admin_level = getattr(row, 'admin_level', 15)
    indexed_date = getattr(row, 'indexed_date', None)
    if indexed_date is not None:
        result.indexed_date = indexed_date.replace(tzinfo=dt.timezone.utc)

    await nres.add_result_details(conn, result, details)

    return result


async def get_simple_place(conn: SearchConnection, place: ntyp.PlaceRef,
                             details: ntyp.LookupDetails) -> Optional[nres.SearchResult]:
    """ Retrieve a place as a simple search result from the database.
    """
    log().function('get_simple_place', place=place, details=details)

    def _add_geometry(sql: SaSelect, col: SaColumn) -> SaSelect:
        if not details.geometry_output:
            return sql

        out = []

        if details.geometry_simplification > 0.0:
            col = col.ST_SimplifyPreserveTopology(details.geometry_simplification)

        if details.geometry_output & ntyp.GeometryFormat.GEOJSON:
            out.append(col.ST_AsGeoJSON().label('geometry_geojson'))
        if details.geometry_output & ntyp.GeometryFormat.TEXT:
            out.append(col.ST_AsText().label('geometry_text'))
        if details.geometry_output & ntyp.GeometryFormat.KML:
            out.append(col.ST_AsKML().label('geometry_kml'))
        if details.geometry_output & ntyp.GeometryFormat.SVG:
            out.append(col.ST_AsSVG().label('geometry_svg'))

        return sql.add_columns(*out)


    row_func: RowFunc[nres.SearchResult]
    row, row_func = await find_in_all_tables(conn, place, _add_geometry)

    if row is None:
        return None

    result = row_func(row, nres.SearchResult)
    assert result is not None

    # add missing details
    assert result is not None
    result.bbox = getattr(row, 'bbox', None)

    await nres.add_result_details(conn, result, details)

    return result
