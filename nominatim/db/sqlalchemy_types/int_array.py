# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom type for an array of integers.
"""
from typing import Any, List, cast, Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY

from nominatim.typing import SaDialect, SaColumn

# pylint: disable=all

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
            return ARRAY(sa.Integer()) #pylint: disable=invalid-name

        return IntList()


    class comparator_factory(sa.types.UserDefinedType.Comparator): # type: ignore[type-arg]

        def __add__(self, other: SaColumn) -> 'sa.ColumnOperators':
            """ Concate the array with the given array. If one of the
                operants is null, the value of the other will be returned.
            """
            return sa.func.array_cat(self, other, type_=IntArray)


        def contains(self, other: SaColumn, **kwargs: Any) -> 'sa.ColumnOperators':
            """ Return true if the array contains all the value of the argument
                array.
            """
            return cast('sa.ColumnOperators', self.op('@>', is_comparison=True)(other))


        def overlaps(self, other: SaColumn) -> 'sa.Operators':
            """ Return true if at least one value of the argument is contained
                in the array.
            """
            return self.op('&&', is_comparison=True)(other)
