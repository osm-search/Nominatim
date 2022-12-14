# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of classes for API access via libraries.
"""
from typing import Mapping, Optional, cast, Any
import asyncio
from pathlib import Path

from sqlalchemy import text, event
from sqlalchemy.engine.url import URL
from sqlalchemy.ext.asyncio import create_async_engine
import asyncpg

from nominatim.config import Configuration
from nominatim.apicmd.status import get_status, StatusResult

class NominatimAPIAsync:
    """ API loader asynchornous version.
    """
    def __init__(self, project_dir: Path,
                 environ: Optional[Mapping[str, str]] = None) -> None:
        self.config = Configuration(project_dir, environ)

        dsn = self.config.get_database_params()

        dburl = URL.create(
                   'postgresql+asyncpg',
                   database=dsn.get('dbname'),
                   username=dsn.get('user'), password=dsn.get('password'),
                   host=dsn.get('host'), port=int(dsn['port']) if 'port' in dsn else None,
                   query={k: v for k, v in dsn.items()
                          if k not in ('user', 'password', 'dbname', 'host', 'port')})
        self.engine = create_async_engine(
                         dburl, future=True,
                         connect_args={'server_settings': {
                            'DateStyle': 'sql,european',
                            'max_parallel_workers_per_gather': '0'
                         }})
        asyncio.get_event_loop().run_until_complete(self._query_server_version())
        asyncio.get_event_loop().run_until_complete(self.close())

        if self.server_version >= 110000:
            @event.listens_for(self.engine.sync_engine, "connect") # type: ignore[misc]
            def _on_connect(dbapi_con: Any, _: Any) -> None:
                cursor = dbapi_con.cursor()
                cursor.execute("SET jit_above_cost TO '-1'")


    async def _query_server_version(self) -> None:
        try:
            async with self.engine.begin() as conn:
                result = await conn.scalar(text('SHOW server_version_num'))
                self.server_version = int(cast(str, result))
        except asyncpg.PostgresError:
            self.server_version = 0

    async def close(self) -> None:
        """ Close all active connections to the database. The NominatimAPIAsync
            object remains usable after closing. If a new API functions is
            called, new connections are created.
        """
        await self.engine.dispose()


    async def status(self) -> StatusResult:
        """ Return the status of the database.
        """
        return await get_status(self.engine)


class NominatimAPI:
    """ API loader, synchronous version.
    """

    def __init__(self, project_dir: Path,
                 environ: Optional[Mapping[str, str]] = None) -> None:
        self.async_api = NominatimAPIAsync(project_dir, environ)


    def close(self) -> None:
        """ Close all active connections to the database. The NominatimAPIAsync
            object remains usable after closing. If a new API functions is
            called, new connections are created.
        """
        asyncio.get_event_loop().run_until_complete(self.async_api.close())


    def status(self) -> StatusResult:
        """ Return the status of the database.
        """
        return asyncio.get_event_loop().run_until_complete(self.async_api.status())
