# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom types for SQLAlchemy.
"""
from __future__ import annotations
from typing import Callable, Any, cast
import sys

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy import types

from nominatim.typing import SaColumn, SaBind

#pylint: disable=all

class Geometry_DistanceSpheroid(sa.sql.expression.FunctionElement[float]):
    """ Function to compute the spherical distance in meters.
    """
    type = sa.Float()
    name = 'Geometry_DistanceSpheroid'
    inherit_cache = True


@compiles(Geometry_DistanceSpheroid) # type: ignore[no-untyped-call, misc]
def _default_distance_spheroid(element: SaColumn,
                               compiler: 'sa.Compiled', **kw: Any) -> str:
    return "ST_DistanceSpheroid(%s,"\
           " 'SPHEROID[\"WGS 84\",6378137,298.257223563, AUTHORITY[\"EPSG\",\"7030\"]]')"\
             % compiler.process(element.clauses, **kw)


@compiles(Geometry_DistanceSpheroid, 'sqlite') # type: ignore[no-untyped-call, misc]
def _spatialite_distance_spheroid(element: SaColumn,
                                  compiler: 'sa.Compiled', **kw: Any) -> str:
    return "Distance(%s, true)" % compiler.process(element.clauses, **kw)


class Geometry(types.UserDefinedType): # type: ignore[type-arg]
    """ Simplified type decorator for PostGIS geometry. This type
        only supports geometries in 4326 projection.
    """
    cache_ok = True

    def __init__(self, subtype: str = 'Geometry'):
        self.subtype = subtype


    def get_col_spec(self) -> str:
        return f'GEOMETRY({self.subtype}, 4326)'


    def bind_processor(self, dialect: 'sa.Dialect') -> Callable[[Any], str]:
        def process(value: Any) -> str:
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


    class comparator_factory(types.UserDefinedType.Comparator): # type: ignore[type-arg]

        def intersects(self, other: SaColumn) -> 'sa.Operators':
            return self.op('&&')(other)

        def is_line_like(self) -> SaColumn:
            return sa.func.ST_GeometryType(self, type_=sa.String).in_(('ST_LineString',
                                                                       'ST_MultiLineString'))

        def is_area(self) -> SaColumn:
            return sa.func.ST_GeometryType(self, type_=sa.String).in_(('ST_Polygon',
                                                                       'ST_MultiPolygon'))


        def ST_DWithin(self, other: SaColumn, distance: SaColumn) -> SaColumn:
            return sa.func.ST_DWithin(self, other, distance, type_=sa.Boolean)


        def ST_DWithin_no_index(self, other: SaColumn, distance: SaColumn) -> SaColumn:
            return sa.func.ST_DWithin(sa.func.coalesce(sa.null(), self),
                                      other, distance, type_=sa.Boolean)


        def ST_Intersects_no_index(self, other: SaColumn) -> 'sa.Operators':
            return sa.func.coalesce(sa.null(), self).op('&&')(other)


        def ST_Distance(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_Distance(self, other, type_=sa.Float)


        def ST_Contains(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_Contains(self, other, type_=sa.Boolean)


        def ST_CoveredBy(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_CoveredBy(self, other, type_=sa.Boolean)


        def ST_ClosestPoint(self, other: SaColumn) -> SaColumn:
            return sa.func.ST_ClosestPoint(self, other, type_=Geometry)


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


@compiles(Geometry, 'sqlite') # type: ignore[no-untyped-call]
def get_col_spec(self, *args, **kwargs): # type: ignore[no-untyped-def]
    return 'GEOMETRY'


SQLITE_FUNCTION_ALIAS = (
    ('ST_AsEWKB', sa.Text, 'AsEWKB'),
    ('ST_GeomFromEWKT', Geometry, 'GeomFromEWKT'),
    ('ST_AsGeoJSON', sa.Text, 'AsGeoJSON'),
    ('ST_AsKML', sa.Text, 'AsKML'),
    ('ST_AsSVG', sa.Text, 'AsSVG'),
)

def _add_function_alias(func: str, ftype: type, alias: str) -> None:
    _FuncDef = type(func, (sa.sql.functions.GenericFunction, ), {
        "type": ftype,
        "name": func,
        "identifier": func,
        "inherit_cache": True})

    func_templ = f"{alias}(%s)"

    def _sqlite_impl(element: Any, compiler: Any, **kw: Any) -> Any:
        return func_templ % compiler.process(element.clauses, **kw)

    compiles(_FuncDef, 'sqlite')(_sqlite_impl) # type: ignore[no-untyped-call]

for alias in SQLITE_FUNCTION_ALIAS:
    _add_function_alias(*alias)



