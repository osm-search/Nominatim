# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of place lookup by ID.
"""
from typing import Optional

import sqlalchemy as sa

from nominatim.typing import SaColumn, SaLabel, SaRow
from nominatim.api.connection import SearchConnection
import nominatim.api.types as ntyp
import nominatim.api.results as nres

def _select_column_geometry(column: SaColumn,
                            geometry_output: ntyp.GeometryFormat) -> SaLabel:
    """ Create the appropriate column expression for selecting a
        geometry for the details response.
    """
    if geometry_output & ntyp.GeometryFormat.GEOJSON:
        return sa.literal_column(f"""
                  ST_AsGeoJSON(CASE WHEN ST_NPoints({column.name}) > 5000
                               THEN ST_SimplifyPreserveTopology({column.name}, 0.0001)
                               ELSE {column.name} END)
                  """).label('geometry_geojson')

    return sa.func.ST_GeometryType(column).label('geometry_type')


async def find_in_placex(conn: SearchConnection, place: ntyp.PlaceRef,
                         details: ntyp.LookupDetails) -> Optional[SaRow]:
    """ Search for the given place in the placex table and return the
        base information.
    """
    t = conn.t.placex
    sql = sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                    t.c.class_, t.c.type, t.c.admin_level,
                    t.c.address, t.c.extratags,
                    t.c.housenumber, t.c.postcode, t.c.country_code,
                    t.c.importance, t.c.wikipedia, t.c.indexed_date,
                    t.c.parent_place_id, t.c.rank_address, t.c.rank_search,
                    t.c.linked_place_id,
                    sa.func.ST_X(t.c.centroid).label('x'),
                    sa.func.ST_Y(t.c.centroid).label('y'),
                    _select_column_geometry(t.c.geometry, details.geometry_output))

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

    return (await conn.execute(sql)).one_or_none()


async def find_in_osmline(conn: SearchConnection, place: ntyp.PlaceRef,
                          details: ntyp.LookupDetails) -> Optional[SaRow]:
    """ Search for the given place in the osmline table and return the
        base information.
    """
    t = conn.t.osmline
    sql = sa.select(t.c.place_id, t.c.osm_id, t.c.parent_place_id,
                    t.c.indexed_date, t.c.startnumber, t.c.endnumber,
                    t.c.step, t.c.address, t.c.postcode, t.c.country_code,
                    sa.func.ST_X(sa.func.ST_Centroid(t.c.linegeo)).label('x'),
                    sa.func.ST_Y(sa.func.ST_Centroid(t.c.linegeo)).label('y'),
                    _select_column_geometry(t.c.linegeo, details.geometry_output))

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

    return (await conn.execute(sql)).one_or_none()


async def find_in_tiger(conn: SearchConnection, place: ntyp.PlaceRef,
                        details: ntyp.LookupDetails) -> Optional[SaRow]:
    """ Search for the given place in the table of Tiger addresses and return
        the base information. Only lookup by place ID is supported.
    """
    t = conn.t.tiger
    sql = sa.select(t.c.place_id, t.c.parent_place_id,
                    t.c.startnumber, t.c.endnumber, t.c.step,
                    t.c.postcode,
                    sa.func.ST_X(sa.func.ST_Centroid(t.c.linegeo)).label('x'),
                    sa.func.ST_Y(sa.func.ST_Centroid(t.c.linegeo)).label('y'),
                    _select_column_geometry(t.c.linegeo, details.geometry_output))

    if isinstance(place, ntyp.PlaceID):
        sql = sql.where(t.c.place_id == place.place_id)
    else:
        return None

    return (await conn.execute(sql)).one_or_none()


async def find_in_postcode(conn: SearchConnection, place: ntyp.PlaceRef,
                           details: ntyp.LookupDetails) -> Optional[SaRow]:
    """ Search for the given place in the postcode table and return the
        base information. Only lookup by place ID is supported.
    """
    t = conn.t.postcode
    sql = sa.select(t.c.place_id, t.c.parent_place_id,
                    t.c.rank_search, t.c.rank_address,
                    t.c.indexed_date, t.c.postcode, t.c.country_code,
                    sa.func.ST_X(t.c.geometry).label('x'),
                    sa.func.ST_Y(t.c.geometry).label('y'),
                    _select_column_geometry(t.c.geometry, details.geometry_output))

    if isinstance(place, ntyp.PlaceID):
        sql = sql.where(t.c.place_id == place.place_id)
    else:
        return None

    return (await conn.execute(sql)).one_or_none()


async def get_place_by_id(conn: SearchConnection, place: ntyp.PlaceRef,
                          details: ntyp.LookupDetails) -> Optional[nres.SearchResult]:
    """ Retrieve a place with additional details from the database.
    """
    if details.geometry_output and details.geometry_output != ntyp.GeometryFormat.GEOJSON:
        raise ValueError("lookup only supports geojosn polygon output.")

    row = await find_in_placex(conn, place, details)
    if row is not None:
        result = nres.create_from_placex_row(row)
        await nres.add_result_details(conn, result, details)
        return result

    row = await find_in_osmline(conn, place, details)
    if row is not None:
        result = nres.create_from_osmline_row(row)
        await nres.add_result_details(conn, result, details)
        return result

    row = await find_in_postcode(conn, place, details)
    if row is not None:
        result = nres.create_from_postcode_row(row)
        await nres.add_result_details(conn, result, details)
        return result

    row = await find_in_tiger(conn, place, details)
    if row is not None:
        result = nres.create_from_tiger_row(row)
        await nres.add_result_details(conn, result, details)
        return result

    # Nothing found under this ID.
    return None
