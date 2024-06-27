# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Common json type for different dialects.
"""
from typing import Any

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.sqlite import JSON as sqlite_json

from ...typing import SaDialect

# pylint: disable=all

class Json(sa.types.TypeDecorator[Any]):
    """ Dialect-independent type for JSON.
    """
    impl = sa.types.JSON
    cache_ok = True

    def load_dialect_impl(self, dialect: SaDialect) -> sa.types.TypeEngine[Any]:
        if dialect.name == 'postgresql':
            return JSONB(none_as_null=True) # type: ignore[no-untyped-call]

        return sqlite_json(none_as_null=True)
