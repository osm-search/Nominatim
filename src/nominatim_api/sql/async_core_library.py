# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Import the base library to use with asynchronous SQLAlchemy.
"""
from typing import Any

# flake8: noqa

try:
    import sqlalchemy.dialects.postgresql.psycopg
    import psycopg
    PGCORE_LIB = 'psycopg'
    PGCORE_ERROR: Any = psycopg.Error
except ModuleNotFoundError:
    import sqlalchemy.dialects.postgresql.asyncpg
    import asyncpg
    PGCORE_LIB = 'asyncpg'
    PGCORE_ERROR = asyncpg.PostgresError
