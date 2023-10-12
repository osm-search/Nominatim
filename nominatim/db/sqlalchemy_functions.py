# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom functions and expressions for SQLAlchemy.
"""
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles

from nominatim.typing import SaColumn

# pylint: disable=abstract-method,missing-function-docstring,consider-using-f-string

def select_index_placex_geometry_reverse_lookuppolygon(table: str) -> 'sa.TextClause':
    """ Create an expression with the necessary conditions over a placex
        table that the index 'idx_placex_geometry_reverse_lookupPolygon'
        can be used.
    """
    return sa.text(f"ST_GeometryType({table}.geometry) in ('ST_Polygon', 'ST_MultiPolygon')"
                   f" AND {table}.rank_address between 4 and 25"
                   f" AND {table}.type != 'postcode'"
                   f" AND {table}.name is not null"
                   f" AND {table}.indexed_status = 0"
                   f" AND {table}.linked_place_id is null")

def select_index_placex_geometry_reverse_lookupplacenode(table: str) -> 'sa.TextClause':
    """ Create an expression with the necessary conditions over a placex
        table that the index 'idx_placex_geometry_reverse_lookupPlaceNode'
        can be used.
    """
    return sa.text(f"{table}.rank_address between 4 and 25"
                   f" AND {table}.type != 'postcode'"
                   f" AND {table}.name is not null"
                   f" AND {table}.linked_place_id is null"
                   f" AND {table}.osm_type = 'N'")


class CrosscheckNames(sa.sql.functions.GenericFunction[bool]):
    """ Check if in the given list of names in parameters 1 any of the names
        from the JSON array in parameter 2 are contained.
    """
    type = sa.Boolean()
    name = 'CrosscheckNames'
    inherit_cache = True

@compiles(CrosscheckNames) # type: ignore[no-untyped-call, misc]
def compile_crosscheck_names(element: SaColumn,
                             compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "coalesce(avals(%s) && ARRAY(SELECT * FROM json_array_elements_text(%s)), false)" % (
            compiler.process(arg1, **kw), compiler.process(arg2, **kw))


@compiles(CrosscheckNames, 'sqlite') # type: ignore[no-untyped-call, misc]
def compile_sqlite_crosscheck_names(element: SaColumn,
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
def default_json_array_each(element: SaColumn, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "json_array_elements(%s)" % compiler.process(element.clauses, **kw)


@compiles(JsonArrayEach, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_json_array_each(element: SaColumn, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "json_each(%s)" % compiler.process(element.clauses, **kw)


class Greatest(sa.sql.functions.GenericFunction[Any]):
    """ Function to compute maximum of all its input parameters.
    """
    name = 'greatest'
    inherit_cache = True


@compiles(Greatest, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_greatest(element: SaColumn, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "max(%s)" % compiler.process(element.clauses, **kw)
