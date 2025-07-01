# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Interface for classes implementing a database search.
"""
from typing import Callable, List
import abc

import sqlalchemy as sa

from ...typing import SaFromClause, SaSelect, SaColumn, SaExpression, SaLambdaSelect
from ...sql.sqlalchemy_types import Geometry
from ...connection import SearchConnection
from ...types import SearchDetails, DataLayer, GeometryFormat
from ...results import SearchResults


class AbstractSearch(abc.ABC):
    """ Encapuslation of a single lookup in the database.
    """
    SEARCH_PRIO: int = 2

    def __init__(self, penalty: float) -> None:
        self.penalty = penalty

    @abc.abstractmethod
    async def lookup(self, conn: SearchConnection, details: SearchDetails) -> SearchResults:
        """ Find results for the search in the database.
        """


def select_placex(t: SaFromClause) -> SaSelect:
    """ Return the basic select query for placex which returns all
        fields necessary to fill a Nominatim result. 't' must either be
        the placex table or a subquery returning appropriate fields from
        a placex-related query.
    """
    return sa.select(t.c.place_id, t.c.osm_type, t.c.osm_id, t.c.name,
                     t.c.class_, t.c.type,
                     t.c.address, t.c.extratags,
                     t.c.housenumber, t.c.postcode, t.c.country_code,
                     t.c.wikipedia,
                     t.c.parent_place_id, t.c.rank_address, t.c.rank_search,
                     t.c.linked_place_id, t.c.admin_level,
                     t.c.centroid,
                     t.c.geometry.ST_Expand(0).label('bbox'))


def exclude_places(t: SaFromClause) -> Callable[[], SaExpression]:
    """ Return an expression to exclude place IDs from the list in the
        SearchDetails.

        Requires the excluded IDs to be supplied as a bind parameter in SQL.
    """
    return lambda: t.c.place_id.not_in(sa.bindparam('excluded'))


def filter_by_layer(table: SaFromClause, layers: DataLayer) -> SaColumn:
    """ Return an expression that filters the given table by layers.
    """
    orexpr: List[SaExpression] = []
    if layers & DataLayer.ADDRESS and layers & DataLayer.POI:
        orexpr.append(no_index(table.c.rank_address).between(1, 30))
    elif layers & DataLayer.ADDRESS:
        orexpr.append(no_index(table.c.rank_address).between(1, 29))
        orexpr.append(sa.func.IsAddressPoint(table))
    elif layers & DataLayer.POI:
        orexpr.append(sa.and_(no_index(table.c.rank_address) == 30,
                              table.c.class_.not_in(('place', 'building'))))

    if layers & DataLayer.MANMADE:
        exclude = []
        if not layers & DataLayer.RAILWAY:
            exclude.append('railway')
        if not layers & DataLayer.NATURAL:
            exclude.extend(('natural', 'water', 'waterway'))
        orexpr.append(sa.and_(table.c.class_.not_in(tuple(exclude)),
                              no_index(table.c.rank_address) == 0))
    else:
        include = []
        if layers & DataLayer.RAILWAY:
            include.append('railway')
        if layers & DataLayer.NATURAL:
            include.extend(('natural', 'water', 'waterway'))
        orexpr.append(sa.and_(table.c.class_.in_(tuple(include)),
                              no_index(table.c.rank_address) == 0))

    if len(orexpr) == 1:
        return orexpr[0]

    return sa.or_(*orexpr)


def no_index(expr: SaColumn) -> SaColumn:
    """ Wrap the given expression, so that the query planner will
        refrain from using the expression for index lookup.
    """
    return sa.func.coalesce(sa.null(), expr)


def filter_by_area(sql: SaSelect, t: SaFromClause,
                   details: SearchDetails, avoid_index: bool = False) -> SaSelect:
    """ Apply SQL statements for filtering by viewbox and near point,
        if applicable.
    """
    if details.near is not None and details.near_radius is not None:
        if details.near_radius < 0.1 and not avoid_index:
            sql = sql.where(
                t.c.geometry.within_distance(sa.bindparam('near', type_=Geometry),
                                             sa.bindparam('near_radius')))
        else:
            sql = sql.where(
                t.c.geometry.ST_Distance(
                    sa.bindparam('near', type_=Geometry)) <= sa.bindparam('near_radius'))
    if details.viewbox is not None and details.bounded_viewbox:
        sql = sql.where(t.c.geometry.intersects(sa.bindparam('viewbox', type_=Geometry),
                                                use_index=not avoid_index and
                                                details.viewbox.area < 0.2))

    return sql


def add_geometry_columns(sql: SaLambdaSelect, col: SaColumn, details: SearchDetails) -> SaSelect:
    """ Add columns for requested geometry formats and return the new query.
    """
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
