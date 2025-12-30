# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom types for SQLAlchemy.
"""
from __future__ import annotations
from typing import Callable, Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import types

from ...typing import SaColumn, SaBind


class Geometry_DistanceSpheroid(sa.sql.expression.FunctionElement[float]):
    """ Function to compute the spherical distance in meters.
    """
    type = sa.Float()
    name = 'Geometry_DistanceSpheroid'
    inherit_cache = True


@compiles(Geometry_DistanceSpheroid)
def _default_distance_spheroid(element: Geometry_DistanceSpheroid,
                               compiler: 'sa.Compiled', **kw: Any) -> str:
    return "ST_DistanceSpheroid(%s,"\
           " 'SPHEROID[\"WGS 84\",6378137,298.257223563, AUTHORITY[\"EPSG\",\"7030\"]]')"\
             % compiler.process(element.clauses, **kw)


@compiles(Geometry_DistanceSpheroid, 'sqlite')
def _spatialite_distance_spheroid(element: Geometry_DistanceSpheroid,
                                  compiler: 'sa.Compiled', **kw: Any) -> str:
    return "COALESCE(Distance(%s, true), 0.0)" % compiler.process(element.clauses, **kw)


class Geometry_IsLineLike(sa.sql.expression.FunctionElement[Any]):
    """ Check if the geometry is a line or multiline.
    """
    name = 'Geometry_IsLineLike'
    inherit_cache = True


@compiles(Geometry_IsLineLike)
def _default_is_line_like(element: Geometry_IsLineLike,
                          compiler: 'sa.Compiled', **kw: Any) -> str:
    return "ST_GeometryType(%s) IN ('ST_LineString', 'ST_MultiLineString')" % \
               compiler.process(element.clauses, **kw)


@compiles(Geometry_IsLineLike, 'sqlite')
def _sqlite_is_line_like(element: Geometry_IsLineLike,
                         compiler: 'sa.Compiled', **kw: Any) -> str:
    return "ST_GeometryType(%s) IN ('LINESTRING', 'MULTILINESTRING')" % \
               compiler.process(element.clauses, **kw)


class Geometry_IsAreaLike(sa.sql.expression.FunctionElement[Any]):
    """ Check if the geometry is a polygon or multipolygon.
    """
    name = 'Geometry_IsLineLike'
    inherit_cache = True


@compiles(Geometry_IsAreaLike)
def _default_is_area_like(element: Geometry_IsAreaLike,
                          compiler: 'sa.Compiled', **kw: Any) -> str:
    return "ST_GeometryType(%s) IN ('ST_Polygon', 'ST_MultiPolygon')" % \
               compiler.process(element.clauses, **kw)


@compiles(Geometry_IsAreaLike, 'sqlite')
def _sqlite_is_area_like(element: Geometry_IsAreaLike,
                         compiler: 'sa.Compiled', **kw: Any) -> str:
    return "ST_GeometryType(%s) IN ('POLYGON', 'MULTIPOLYGON')" % \
               compiler.process(element.clauses, **kw)


class Geometry_IntersectsBbox(sa.sql.expression.FunctionElement[Any]):
    """ Check if the bounding boxes of the given geometries intersect.
    """
    name = 'Geometry_IntersectsBbox'
    inherit_cache = True


@compiles(Geometry_IntersectsBbox)
def _default_intersects(element: Geometry_IntersectsBbox,
                        compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "%s && %s" % (compiler.process(arg1, **kw), compiler.process(arg2, **kw))


@compiles(Geometry_IntersectsBbox, 'sqlite')
def _sqlite_intersects(element: Geometry_IntersectsBbox,
                       compiler: 'sa.Compiled', **kw: Any) -> str:
    return "MbrIntersects(%s) = 1" % compiler.process(element.clauses, **kw)


class Geometry_ColumnIntersectsBbox(sa.sql.expression.FunctionElement[Any]):
    """ Check if the bounding box of the geometry intersects with the
        given table column, using the spatial index for the column.

        The index must exist or the query may return nothing.
    """
    name = 'Geometry_ColumnIntersectsBbox'
    inherit_cache = True


@compiles(Geometry_ColumnIntersectsBbox)
def default_intersects_column(element: Geometry_ColumnIntersectsBbox,
                              compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "%s && %s" % (compiler.process(arg1, **kw), compiler.process(arg2, **kw))


@compiles(Geometry_ColumnIntersectsBbox, 'sqlite')
def spatialite_intersects_column(element: Geometry_ColumnIntersectsBbox,
                                 compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "MbrIntersects(%s, %s) = 1 and "\
           "%s.ROWID IN (SELECT ROWID FROM SpatialIndex "\
           "             WHERE f_table_name = '%s' AND f_geometry_column = '%s' "\
           "             AND search_frame = %s)"\
        % (compiler.process(arg1, **kw),
           compiler.process(arg2, **kw),
           arg1.table.name, arg1.table.name, arg1.name,
           compiler.process(arg2, **kw))


class Geometry_ColumnDWithin(sa.sql.expression.FunctionElement[Any]):
    """ Check if the geometry is within the distance of the
        given table column, using the spatial index for the column.

        The index must exist or the query may return nothing.
    """
    name = 'Geometry_ColumnDWithin'
    inherit_cache = True


@compiles(Geometry_ColumnDWithin)
def default_dwithin_column(element: Geometry_ColumnDWithin,
                           compiler: 'sa.Compiled', **kw: Any) -> str:
    return "ST_DWithin(%s)" % compiler.process(element.clauses, **kw)


@compiles(Geometry_ColumnDWithin, 'sqlite')
def spatialite_dwithin_column(element: Geometry_ColumnDWithin,
                              compiler: 'sa.Compiled', **kw: Any) -> str:
    geom1, geom2, dist = list(element.clauses)
    return "ST_Distance(%s, %s) < %s and "\
           "%s.ROWID IN (SELECT ROWID FROM SpatialIndex "\
           "             WHERE f_table_name = '%s' AND f_geometry_column = '%s' "\
           "             AND search_frame = ST_Expand(%s, %s))"\
        % (compiler.process(geom1, **kw),
           compiler.process(geom2, **kw),
           compiler.process(dist, **kw),
           geom1.table.name, geom1.table.name, geom1.name,
           compiler.process(geom2, **kw),
           compiler.process(dist, **kw))


class Geometry(types.UserDefinedType):  # type: ignore[type-arg]
    """ Simplified type decorator for PostGIS geometry. This type
        only supports geometries in 4326 projection.
    """
    cache_ok = True

    def __init__(self, subtype: str = 'Geometry'):
        self.subtype = subtype

    def get_col_spec(self, **_: Any) -> str:
        return f'GEOMETRY({self.subtype}, 4326)'

    def bind_processor(self, dialect: 'sa.Dialect') -> Callable[[Any], str]:
        def process(value: Any) -> str:
            if value is None:
                return 'null'
            if isinstance(value, str):
                return value

            return cast(str, value.to_wkt())
        return process

    def result_processor(self, dialect: 'sa.Dialect', coltype: object) -> Callable[[Any], str]:
        def process(value: Any) -> str:
            assert isinstance(value, str)
            return value
        return process

    def column_expression(self, col: SaColumn) -> SaColumn:
        return sa.func.ST_AsEWKB(col)

    def bind_expression(self, bindvalue: SaBind) -> SaColumn:
        return sa.func.ST_GeomFromText(bindvalue, sa.text('4326'), type_=self)

    class comparator_factory(types.UserDefinedType.Comparator):  # type: ignore[type-arg]

        def intersects(self, other: SaColumn, use_index: bool = True) -> 'sa.Operators':
            if not use_index:
                return Geometry_IntersectsBbox(sa.func.coalesce(sa.null(), self.expr), other)

            if isinstance(self.expr, sa.Column):
                return Geometry_ColumnIntersectsBbox(self.expr, other)

            return Geometry_IntersectsBbox(self.expr, other)

        def is_line_like(self) -> SaColumn:
            return Geometry_IsLineLike(self)

        def is_area(self) -> SaColumn:
            return Geometry_IsAreaLike(self)

        def within_distance(self, other: SaColumn, distance: SaColumn) -> SaColumn:
            if isinstance(self.expr, sa.Column):
                return Geometry_ColumnDWithin(self.expr, other, distance)

            return self.ST_Distance(other) < distance

        def ST_Distance(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_Distance(self, other, type_=sa.Float)

        def ST_Contains(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_Contains(self, other, type_=sa.Boolean)

        def ST_CoveredBy(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_CoveredBy(self, other, type_=sa.Boolean)

        def ST_ClosestPoint(self, other: SaColumn) -> SaColumn:
            return sa.func.coalesce(sa.func.ST_ClosestPoint(self, other, type_=Geometry),
                                    other)

        def ST_Buffer(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_Buffer(self, other, type_=Geometry)

        def ST_Expand(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_Expand(self, other, type_=Geometry)

        def ST_Collect(self) -> SaColumn:
            return sa.func.ST_Collect(self, type_=Geometry)

        def ST_Centroid(self) -> SaColumn:
            return sa.func.ST_Centroid(self, type_=Geometry)

        def ST_LineInterpolatePoint(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_LineInterpolatePoint(self, other, type_=Geometry)

        def ST_LineLocatePoint(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_LineLocatePoint(self, other, type_=sa.Float)

        def distance_spheroid(self, other: SaColumn) -> SaColumn:
            return Geometry_DistanceSpheroid(self, other)


@compiles(Geometry, 'sqlite')
def get_col_spec(self, *args, **kwargs):  # type: ignore[no-untyped-def]
    return 'GEOMETRY'


SQLITE_FUNCTION_ALIAS = (
    ('ST_AsEWKB', sa.Text, 'AsEWKB'),
    ('ST_GeomFromEWKT', Geometry, 'GeomFromEWKT'),
    ('ST_AsGeoJSON', sa.Text, 'AsGeoJSON'),
    ('ST_AsKML', sa.Text, 'AsKML'),
    ('ST_AsSVG', sa.Text, 'AsSVG'),
    ('ST_LineLocatePoint', sa.Float, 'ST_Line_Locate_Point'),
    ('ST_LineInterpolatePoint', sa.Float, 'ST_Line_Interpolate_Point'),
)


def _add_function_alias(func: str, ftype: type, alias: str) -> None:
    _FuncDef = type(func, (sa.sql.functions.GenericFunction, ), {
        "type": ftype(),
        "name": func,
        "identifier": func,
        "inherit_cache": True})

    func_templ = f"{alias}(%s)"

    def _sqlite_impl(element: Any, compiler: Any, **kw: Any) -> Any:
        return func_templ % compiler.process(element.clauses, **kw)

    compiles(_FuncDef, 'sqlite')(_sqlite_impl)


for alias in SQLITE_FUNCTION_ALIAS:
    _add_function_alias(*alias)
