# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom type for an array of integers.
"""
from typing import Any, List, Optional

import sqlalchemy as sa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import ARRAY

from ...typing import SaDialect, SaColumn


class IntList(sa.types.TypeDecorator[Any]):
    """ A list of integers saved as a text of comma-separated numbers.
    """
    impl = sa.types.Unicode
    cache_ok = True

    def process_bind_param(self, value: Optional[Any], dialect: 'sa.Dialect') -> Optional[str]:
        if value is None:
            return None

        assert isinstance(value, list)
        return ','.join(map(str, value))

    def process_result_value(self, value: Optional[Any],
                             dialect: SaDialect) -> Optional[List[int]]:
        return [int(v) for v in value.split(',')] if value is not None else None

    def copy(self, **kw: Any) -> 'IntList':
        return IntList(self.impl.length)


class IntArray(sa.types.TypeDecorator[Any]):
    """ Dialect-independent list of integers.
    """
    impl = IntList
    cache_ok = True

    def load_dialect_impl(self, dialect: SaDialect) -> sa.types.TypeEngine[Any]:
        if dialect.name == 'postgresql':
            return ARRAY(sa.Integer())

        return IntList()

    class comparator_factory(sa.types.UserDefinedType.Comparator):  # type: ignore[type-arg]

        def __add__(self, other: SaColumn) -> 'sa.ColumnOperators':
            """ Concate the array with the given array. If one of the
                operants is null, the value of the other will be returned.
            """
            return ArrayCat(self.expr, other)

        def contains(self, other: SaColumn, **kwargs: Any) -> 'sa.ColumnOperators':
            """ Return true if the array contains all the value of the argument
                array.
            """
            return ArrayContains(self.expr, other)


class ArrayAgg(sa.sql.functions.GenericFunction[Any]):
    """ Aggregate function to collect elements in an array.
    """
    type = IntArray()
    identifier = 'ArrayAgg'
    name = 'array_agg'
    inherit_cache = True


@compiles(ArrayAgg, 'sqlite')
def sqlite_array_agg(element: ArrayAgg, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "group_concat(%s, ',')" % compiler.process(element.clauses, **kw)


class ArrayContains(sa.sql.expression.FunctionElement[Any]):
    """ Function to check if an array is fully contained in another.
    """
    name = 'ArrayContains'
    inherit_cache = True


@compiles(ArrayContains)
def generic_array_contains(element: ArrayContains, compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "(%s @> %s)" % (compiler.process(arg1, **kw),
                           compiler.process(arg2, **kw))


@compiles(ArrayContains, 'sqlite')
def sqlite_array_contains(element: ArrayContains, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "array_contains(%s)" % compiler.process(element.clauses, **kw)


class ArrayCat(sa.sql.expression.FunctionElement[Any]):
    """ Function to check if an array is fully contained in another.
    """
    type = IntArray()
    identifier = 'ArrayCat'
    inherit_cache = True


@compiles(ArrayCat)
def generic_array_cat(element: ArrayCat, compiler: 'sa.Compiled', **kw: Any) -> str:
    return "array_cat(%s)" % compiler.process(element.clauses, **kw)


@compiles(ArrayCat, 'sqlite')
def sqlite_array_cat(element: ArrayCat, compiler: 'sa.Compiled', **kw: Any) -> str:
    arg1, arg2 = list(element.clauses)
    return "(%s || ',' || %s)" % (compiler.process(arg1, **kw), compiler.process(arg2, **kw))
