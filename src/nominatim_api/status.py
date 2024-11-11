# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Classes and function related to status call.
"""
from typing import Optional
import datetime as dt
import dataclasses

import sqlalchemy as sa

from .connection import SearchConnection
from .version import NOMINATIM_API_VERSION


@dataclasses.dataclass
class StatusResult:
    """ Result of a call to the status API.
    """
    status: int
    message: str
    software_version = NOMINATIM_API_VERSION
    data_updated: Optional[dt.datetime] = None
    database_version: Optional[str] = None


async def get_status(conn: SearchConnection) -> StatusResult:
    """ Execute a status API call.
    """
    status = StatusResult(0, 'OK')

    # Last update date
    sql = sa.select(conn.t.import_status.c.lastimportdate).limit(1)
    status.data_updated = await conn.scalar(sql)

    if status.data_updated is not None:
        if status.data_updated.tzinfo is None:
            status.data_updated = status.data_updated.replace(tzinfo=dt.timezone.utc)
        else:
            status.data_updated = status.data_updated.astimezone(dt.timezone.utc)

    # Database version
    try:
        status.database_version = await conn.get_property('database_version')
    except ValueError:
        pass

    return status
