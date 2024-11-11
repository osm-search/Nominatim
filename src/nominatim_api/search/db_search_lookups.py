# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of lookup functions for the search_name table.
"""
from typing import List, Any

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles

from ..typing import SaFromClause
from ..sql.sqlalchemy_types import IntArray


LookupType = sa.sql.expression.FunctionElement[Any]


class LookupAll(LookupType):
    """ Find all entries in search_name table that contain all of
        a given list of tokens using an index for the search.
    """
    inherit_cache = True

    def __init__(self, table: SaFromClause, column: str, tokens: List[int]) -> None:
        super().__init__(table.c.place_id, getattr(table.c, column), column,
                         sa.type_coerce(tokens, IntArray))


@compiles(LookupAll)
def _default_lookup_all(element: LookupAll,
                        compiler: 'sa.Compiled', **kw: Any) -> str:
    _, col, _, tokens = list(element.clauses)
    return "(%s @> %s)" % (compiler.process(col, **kw),
                           compiler.process(tokens, **kw))


@compiles(LookupAll, 'sqlite')
def _sqlite_lookup_all(element: LookupAll,
                       compiler: 'sa.Compiled', **kw: Any) -> str:
    place, col, colname, tokens = list(element.clauses)
    return "(%s IN (SELECT CAST(value as bigint) FROM"\
           " (SELECT array_intersect_fuzzy(places) as p FROM"\
           "   (SELECT places FROM reverse_search_name"\
           "   WHERE word IN (SELECT value FROM json_each('[' || %s || ']'))"\
           "     AND column = %s"\
           "   ORDER BY length(places)) as x) as u,"\
           " json_each('[' || u.p || ']'))"\
           " AND array_contains(%s, %s))"\
        % (compiler.process(place, **kw),
           compiler.process(tokens, **kw),
           compiler.process(colname, **kw),
           compiler.process(col, **kw),
           compiler.process(tokens, **kw))


class LookupAny(LookupType):
    """ Find all entries that contain at least one of the given tokens.
        Use an index for the search.
    """
    inherit_cache = True

    def __init__(self, table: SaFromClause, column: str, tokens: List[int]) -> None:
        super().__init__(table.c.place_id, getattr(table.c, column), column,
                         sa.type_coerce(tokens, IntArray))


@compiles(LookupAny)
def _default_lookup_any(element: LookupAny,
                        compiler: 'sa.Compiled', **kw: Any) -> str:
    _, col, _, tokens = list(element.clauses)
    return "(%s && %s)" % (compiler.process(col, **kw),
                           compiler.process(tokens, **kw))


@compiles(LookupAny, 'sqlite')
def _sqlite_lookup_any(element: LookupAny,
                       compiler: 'sa.Compiled', **kw: Any) -> str:
    place, _, colname, tokens = list(element.clauses)
    return "%s IN (SELECT CAST(value as bigint) FROM"\
           " (SELECT array_union(places) as p FROM reverse_search_name"\
           "   WHERE word IN (SELECT value FROM json_each('[' || %s || ']'))"\
           "     AND column = %s) as u,"\
           " json_each('[' || u.p || ']'))" % (compiler.process(place, **kw),
                                               compiler.process(tokens, **kw),
                                               compiler.process(colname, **kw))


class Restrict(LookupType):
    """ Find all entries that contain all of the given tokens.
        Do not use an index for the search.
    """
    inherit_cache = True

    def __init__(self, table: SaFromClause, column: str, tokens: List[int]) -> None:
        super().__init__(getattr(table.c, column),
                         sa.type_coerce(tokens, IntArray))


@compiles(Restrict)
def _default_restrict(element: Restrict,
                      compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "(coalesce(null, %s) @> %s)" % (compiler.process(arg1, **kw),
                                           compiler.process(arg2, **kw))


@compiles(Restrict, 'sqlite')
def _sqlite_restrict(element: Restrict,
                     compiler: 'sa.Compiled', **kw: Any) -> str:
    return "array_contains(%s)" % compiler.process(element.clauses, **kw)
