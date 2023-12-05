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
            return self.op('||')(sa.func.coalesce(other,
                                                  sa.type_coerce('', KeyValueStore)))


        def has_key(self, key: SaColumn) -> 'sa.Operators':
            """ Return true if the key is cotained in the store.
            """
            return self.op('?', is_comparison=True)(key)
