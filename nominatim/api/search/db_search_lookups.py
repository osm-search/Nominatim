# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of lookup functions for the search_name table.
"""
from typing import List, Any

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles

from nominatim.typing import SaFromClause
from nominatim.db.sqlalchemy_types import IntArray

# pylint: disable=consider-using-f-string

LookupType = sa.sql.expression.FunctionElement[Any]

class LookupAll(LookupType):
    """ Find all entries in search_name table that contain all of
        a given list of tokens using an index for the search.
    """
    inherit_cache = True

    def __init__(self, table: SaFromClause, column: str, tokens: List[int]) -> None:
        super().__init__(getattr(table.c, column),
                         sa.type_coerce(tokens, IntArray))


@compiles(LookupAll) # type: ignore[no-untyped-call, misc]
def _default_lookup_all(element: LookupAll,
                        compiler: 'sa.Compiled', **kw: Any) -> str:
    col, tokens = list(element.clauses)
    return "(%s @> %s)" % (compiler.process(col, **kw),
                           compiler.process(tokens, **kw))



class LookupAny(LookupType):
    """ Find all entries that contain at least one of the given tokens.
        Use an index for the search.
    """
    inherit_cache = True

    def __init__(self, table: SaFromClause, column: str, tokens: List[int]) -> None:
        super().__init__(getattr(table.c, column),
                         sa.type_coerce(tokens, IntArray))


@compiles(LookupAny) # type: ignore[no-untyped-call, misc]
def _default_lookup_any(element: LookupAny,
                        compiler: 'sa.Compiled', **kw: Any) -> str:
    col, tokens = list(element.clauses)
    return "(%s && %s)" % (compiler.process(col, **kw),
                           compiler.process(tokens, **kw))



class Restrict(LookupType):
    """ Find all entries that contain all of the given tokens.
        Do not use an index for the search.
    """
    inherit_cache = True

    def __init__(self, table: SaFromClause, column: str, tokens: List[int]) -> None:
        super().__init__(getattr(table.c, column),
                         sa.type_coerce(tokens, IntArray))


@compiles(Restrict) # type: ignore[no-untyped-call, misc]
def _default_restrict(element: Restrict,
                        compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "(coalesce(null, %s) @> %s)" % (compiler.process(arg1, **kw),
                                           compiler.process(arg2, **kw))
