# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
A custom type that implements a simple key-value store of strings.
"""
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import HSTORE
from sqlalchemy.dialects.sqlite import JSON as sqlite_json

from nominatim.typing import SaDialect, SaColumn

# pylint: disable=all

class KeyValueStore(sa.types.TypeDecorator[Any]):
    """ Dialect-independent type of a simple key-value store of strings.
    """
    impl = HSTORE
    cache_ok = True

    def load_dialect_impl(self, dialect: SaDialect) -> sa.types.TypeEngine[Any]:
        if dialect.name == 'postgresql':
            return HSTORE() # type: ignore[no-untyped-call]

        return sqlite_json(none_as_null=True)


    class comparator_factory(sa.types.UserDefinedType.Comparator): # type: ignore[type-arg]

        def merge(self, other: SaColumn) -> 'sa.Operators':
            """ Merge the values from the given KeyValueStore into this
                one, overwriting values where necessary. When the argument
                is null, nothing happens.
            """
            return KeyValueConcat(self.expr, other)


class KeyValueConcat(sa.sql.expression.FunctionElement[Any]):
    """ Return the merged key-value store from the input parameters.
    """
    type = KeyValueStore()
    name = 'JsonConcat'
    inherit_cache = True

@compiles(KeyValueConcat) # type: ignore[no-untyped-call, misc]
def default_json_concat(element: KeyValueConcat, compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "(%s || coalesce(%s, ''::hstore))" % (compiler.process(arg1, **kw), compiler.process(arg2, **kw))

@compiles(KeyValueConcat, 'sqlite') # type: ignore[no-untyped-call, misc]
def sqlite_json_concat(element: KeyValueConcat, compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "json_patch(%s, coalesce(%s, '{}'))" % (compiler.process(arg1, **kw), compiler.process(arg2, **kw))



