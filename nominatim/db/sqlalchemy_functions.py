# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom functions and expressions for SQLAlchemy.
"""
from __future__ import annotations
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles

from nominatim.typing import SaColumn

# pylint: disable=all

class PlacexGeometryReverseLookuppolygon(sa.sql.functions.GenericFunction[Any]):
    """ Check for conditions that allow partial index use on
        'idx_placex_geometry_reverse_lookupPolygon'.

        Needs to be constant, so that the query planner picks them up correctly
        in prepared statements.
    """
    name = 'PlacexGeometryReverseLookuppolygon'
    inherit_cache = True


@compiles(PlacexGeometryReverseLookuppolygon) # type: ignore[no-untyped-call, misc]
def _default_intersects(element: PlacexGeometryReverseLookuppolygon,
                        compiler: 'sa.Compiled', **kw: Any) -> str:
    return ("(ST_GeometryType(placex.geometry) in ('ST_Polygon', 'ST_MultiPolygon')"
            " AND placex.rank_address between 4 and 25"
            " AND placex.type != 'postcode'"
            " AND placex.name is not null"
            " AND placex.indexed_status = 0"
            " AND placex.linked_place_id is null)")


@compiles(PlacexGeometryReverseLookuppolygon, 'sqlite') # type: ignore[no-untyped-call, misc]
def _sqlite_intersects(element: PlacexGeometryReverseLookuppolygon,
                       compiler: 'sa.Compiled', **kw: Any) -> str:
    return ("(ST_GeometryType(placex.geometry) in ('POLYGON', 'MULTIPOLYGON')"
            " AND placex.rank_address between 4 and 25"
            " AND placex.type != 'postcode'"
            " AND placex.name is not null"
            " AND placex.indexed_status = 0"
            " AND placex.linked_place_id is null)")


class IntersectsReverseDistance(sa.sql.functions.GenericFunction[Any]):
    name = 'IntersectsReverseDistance'
    inherit_cache = True

    def __init__(self, table: sa.Table, geom: SaColumn) -> None:
        super().__init__(table.c.geometry, # type: ignore[no-untyped-call]
                         table.c.rank_search, geom)
        self.tablename = table.name


@compiles(IntersectsReverseDistance) # type: ignore[no-untyped-call, misc]
def default_reverse_place_diameter(element: IntersectsReverseDistance,
                                   compiler: 'sa.Compiled', **kw: Any) -> str:
    table = element.tablename
    return f"({table}.rank_address between 4 and 25"\
           f" AND {table}.type != 'postcode'"\
           f" AND {table}.name is not null"\
           f" AND {table}.linked_place_id is null"\
           f" AND {table}.osm_type = 'N'" + \
           " AND ST_Buffer(%s, reverse_place_diameter(%s)) && %s)" % \
               tuple(map(lambda c: compiler.process(c, **kw), element.clauses))


@compiles(IntersectsReverseDistance, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_reverse_place_diameter(element: IntersectsReverseDistance,
                                  compiler: 'sa.Compiled', **kw: Any) -> str:
    geom1, rank, geom2 = list(element.clauses)
    table = element.tablename

    return (f"({table}.rank_address between 4 and 25"\
            f" AND {table}.type != 'postcode'"\
            f" AND {table}.name is not null"\
            f" AND {table}.linked_place_id is null"\
            f" AND {table}.osm_type = 'N'"\
             " AND MbrIntersects(%s, ST_Expand(%s, 14.0 * exp(-0.2 * %s) - 0.03))"\
            f" AND {table}.place_id IN"\
             " (SELECT place_id FROM placex_place_node_areas"\
             "  WHERE ROWID IN (SELECT ROWID FROM SpatialIndex"\
             "  WHERE f_table_name = 'placex_place_node_areas'"\
             "  AND search_frame = %s)))") % (
                compiler.process(geom1, **kw),
                compiler.process(geom2, **kw),
                compiler.process(rank, **kw),
                compiler.process(geom2, **kw))


class IsBelowReverseDistance(sa.sql.functions.GenericFunction[Any]):
    name = 'IsBelowReverseDistance'
    inherit_cache = True


@compiles(IsBelowReverseDistance) # type: ignore[no-untyped-call, misc]
def default_is_below_reverse_distance(element: IsBelowReverseDistance,
                                      compiler: 'sa.Compiled', **kw: Any) -> str:
    dist, rank = list(element.clauses)
    return "%s < reverse_place_diameter(%s)" % (compiler.process(dist, **kw),
                                                compiler.process(rank, **kw))


@compiles(IsBelowReverseDistance, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_is_below_reverse_distance(element: IsBelowReverseDistance,
                                     compiler: 'sa.Compiled', **kw: Any) -> str:
    dist, rank = list(element.clauses)
    return "%s < 14.0 * exp(-0.2 * %s) - 0.03" % (compiler.process(dist, **kw),
                                                  compiler.process(rank, **kw))


class IsAddressPoint(sa.sql.functions.GenericFunction[Any]):
    name = 'IsAddressPoint'
    inherit_cache = True

    def __init__(self, table: sa.Table) -> None:
        super().__init__(table.c.rank_address, # type: ignore[no-untyped-call]
                         table.c.housenumber, table.c.name)


@compiles(IsAddressPoint) # type: ignore[no-untyped-call, misc]
def default_is_address_point(element: IsAddressPoint,
                             compiler: 'sa.Compiled', **kw: Any) -> str:
    rank, hnr, name = list(element.clauses)
    return "(%s = 30 AND (%s IS NOT NULL OR %s ? 'addr:housename'))" % (
                compiler.process(rank, **kw),
                compiler.process(hnr, **kw),
                compiler.process(name, **kw))


@compiles(IsAddressPoint, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_is_address_point(element: IsAddressPoint,
                            compiler: 'sa.Compiled', **kw: Any) -> str:
    rank, hnr, name = list(element.clauses)
    return "(%s = 30 AND coalesce(%s, json_extract(%s, '$.addr:housename')) IS NOT NULL)" % (
                compiler.process(rank, **kw),
                compiler.process(hnr, **kw),
                compiler.process(name, **kw))


class CrosscheckNames(sa.sql.functions.GenericFunction[Any]):
    """ Check if in the given list of names in parameters 1 any of the names
        from the JSON array in parameter 2 are contained.
    """
    name = 'CrosscheckNames'
    inherit_cache = True

@compiles(CrosscheckNames) # type: ignore[no-untyped-call, misc]
def compile_crosscheck_names(element: CrosscheckNames,
                             compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "coalesce(avals(%s) && ARRAY(SELECT * FROM json_array_elements_text(%s)), false)" % (
            compiler.process(arg1, **kw), compiler.process(arg2, **kw))


@compiles(CrosscheckNames, 'sqlite') # type: ignore[no-untyped-call, misc]
def compile_sqlite_crosscheck_names(element: CrosscheckNames,
                                    compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "EXISTS(SELECT *"\
           " FROM json_each(%s) as name, json_each(%s) as match_name"\
           " WHERE name.value = match_name.value)"\
           % (compiler.process(arg1, **kw), compiler.process(arg2, **kw))


class JsonArrayEach(sa.sql.functions.GenericFunction[Any]):
    """ Return elements of a json array as a set.
    """
    name = 'JsonArrayEach'
    inherit_cache = True


@compiles(JsonArrayEach) # type: ignore[no-untyped-call, misc]
def default_json_array_each(element: JsonArrayEach, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "json_array_elements(%s)" % compiler.process(element.clauses, **kw)


@compiles(JsonArrayEach, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_json_array_each(element: JsonArrayEach, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "json_each(%s)" % compiler.process(element.clauses, **kw)


class Greatest(sa.sql.functions.GenericFunction[Any]):
    """ Function to compute maximum of all its input parameters.
    """
    name = 'greatest'
    inherit_cache = True


@compiles(Greatest, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_greatest(element: Greatest, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "max(%s)" % compiler.process(element.clauses, **kw)
