# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Classes and function releated to status call.
"""
from typing import Optional, cast
import datetime as dt

import sqlalchemy as sa
from sqlalchemy.ext.asyncio.engine import AsyncConnection
import asyncpg

from nominatim import version

class StatusResult:
    """ Result of a call to the status API.
    """

    def __init__(self, status: int, msg: str):
        self.status = status
        self.message = msg
        self.software_version = version.NOMINATIM_VERSION
        self.data_updated: Optional[dt.datetime]  = None
        self.database_version: Optional[version.NominatimVersion] = None


async def _get_database_date(conn: AsyncConnection) -> Optional[dt.datetime]:
    """ Query the database date.
    """
    sql = sa.text('SELECT lastimportdate FROM import_status LIMIT 1')
    result = await conn.execute(sql)

    for row in result:
        return cast(dt.datetime, row[0])

    return None


async def _get_database_version(conn: AsyncConnection) -> Optional[version.NominatimVersion]:
    sql = sa.text("""SELECT value FROM nominatim_properties
                     WHERE property = 'database_version'""")
    result = await conn.execute(sql)

    for row in result:
        return version.parse_version(cast(str, row[0]))

    return None


async def get_status(conn: AsyncConnection) -> StatusResult:
    """ Execute a status API call.
    """
    status = StatusResult(0, 'OK')
    try:
        status.data_updated = await _get_database_date(conn)
        status.database_version = await _get_database_version(conn)
    except asyncpg.PostgresError:
        return StatusResult(700, 'Database connection failed')

    return status
