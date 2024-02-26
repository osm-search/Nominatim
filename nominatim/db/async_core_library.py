# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Import the base library to use with asynchronous SQLAlchemy.
"""
# pylint: disable=invalid-name

from typing import Any

try:
    import psycopg
    PGCORE_LIB = 'psycopg'
    PGCORE_ERROR: Any = psycopg.Error
except ModuleNotFoundError:
    import asyncpg
    PGCORE_LIB = 'asyncpg'
    PGCORE_ERROR = asyncpg.PostgresError
