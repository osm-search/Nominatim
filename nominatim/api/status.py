# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Classes and function releated to status call.
"""
from typing import Optional
import datetime as dt
import dataclasses

import sqlalchemy as sa

from nominatim.api.connection import SearchConnection
from nominatim import version

@dataclasses.dataclass
class StatusResult:
    """ Result of a call to the status API.
    """
    status: int
    message: str
    software_version = version.NOMINATIM_VERSION
    data_updated: Optional[dt.datetime] = None
    database_version: Optional[version.NominatimVersion] = None


async def get_status(conn: SearchConnection) -> StatusResult:
    """ Execute a status API call.
    """
    status = StatusResult(0, 'OK')

    # Last update date
    sql = sa.select(conn.t.import_status.c.lastimportdate).limit(1)
    status.data_updated = await conn.scalar(sql)

    # Database version
    try:
        verstr = await conn.get_property('database_version')
        status.database_version = version.parse_version(verstr)
    except ValueError:
        pass

    return status
