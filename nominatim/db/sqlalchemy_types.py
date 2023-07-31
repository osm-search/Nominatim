# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom types for SQLAlchemy.
"""
from typing import Callable, Any, cast
import sys

import sqlalchemy as sa
from sqlalchemy import types

from nominatim.typing import SaColumn, SaBind

#pylint: disable=all

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
            return sa.func.ST_DWithin(self, other, distance, type_=sa.Float)


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
