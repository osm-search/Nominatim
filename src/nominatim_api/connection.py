# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Extended SQLAlchemy connection class that also includes access to the schema.
"""
from typing import cast, Any, Mapping, Sequence, Union, Dict, Optional, Set, \
                   Awaitable, Callable, TypeVar
import asyncio

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from .typing import SaFromClause
from .sql.sqlalchemy_schema import SearchTables
from .sql.sqlalchemy_types import Geometry
from .logging import log

T = TypeVar('T')


class SearchConnection:
    """ An extended SQLAlchemy connection class, that also contains
        the table definitions. The underlying asynchronous SQLAlchemy
        connection can be accessed with the 'connection' property.
        The 't' property is the collection of Nominatim tables.
    """

    def __init__(self, conn: AsyncConnection,
                 tables: SearchTables,
                 properties: Dict[str, Any]) -> None:
        self.connection = conn
        self.t = tables
        self._property_cache = properties
        self._classtables: Optional[Set[str]] = None
        self.query_timeout: Optional[int] = None

    def set_query_timeout(self, timeout: Optional[int]) -> None:
        """ Set the timeout after which a query over this connection
            is cancelled.
        """
        self.query_timeout = timeout

    async def scalar(self, sql: sa.sql.base.Executable,
                     params: Union[Mapping[str, Any], None] = None) -> Any:
        """ Execute a 'scalar()' query on the connection.
        """
        log().sql(self.connection, sql, params)
        return await asyncio.wait_for(self.connection.scalar(sql, params), self.query_timeout)

    async def execute(self, sql: 'sa.Executable',
                      params: Union[Mapping[str, Any], Sequence[Mapping[str, Any]], None] = None
                      ) -> 'sa.Result[Any]':
        """ Execute a 'execute()' query on the connection.
        """
        log().sql(self.connection, sql, params)
        return await asyncio.wait_for(self.connection.execute(sql, params), self.query_timeout)

    async def get_property(self, name: str, cached: bool = True) -> str:
        """ Get a property from Nominatim's property table.

            Property values are normally cached so that they are only
            retrieved from the database when they are queried for the
            first time with this function. Set 'cached' to False to force
            reading the property from the database.

            Raises a ValueError if the property does not exist.
        """
        lookup_name = f'DBPROP:{name}'

        if cached and lookup_name in self._property_cache:
            return cast(str, self._property_cache[lookup_name])

        sql = sa.select(self.t.properties.c.value)\
            .where(self.t.properties.c.property == name)
        value = await self.connection.scalar(sql)

        if value is None:
            raise ValueError(f"Property '{name}' not found in database.")

        self._property_cache[lookup_name] = cast(str, value)

        return cast(str, value)

    async def get_db_property(self, name: str) -> Any:
        """ Get a setting from the database. At the moment, only
            'server_version', the version of the database software, can
            be retrieved with this function.

            Raises a ValueError if the property does not exist.
        """
        if name != 'server_version':
            raise ValueError(f"DB setting '{name}' not found in database.")

        return self._property_cache['DB:server_version']

    async def get_cached_value(self, group: str, name: str,
                               factory: Callable[[], Awaitable[T]]) -> T:
        """ Access the cache for this Nominatim instance.
            Each cache value needs to belong to a group and have a name.
            This function is for internal API use only.

            `factory` is an async callback function that produces
            the value if it is not already cached.

            Returns the cached value or the result of factory (also caching
            the result).
        """
        full_name = f'{group}:{name}'

        if full_name in self._property_cache:
            return cast(T, self._property_cache[full_name])

        value = await factory()
        self._property_cache[full_name] = value

        return value

    async def get_class_table(self, cls: str, typ: str) -> Optional[SaFromClause]:
        """ Lookup up if there is a classtype table for the given category
            and return a SQLAlchemy table for it, if it exists.
        """
        if self._classtables is None:
            res = await self.execute(sa.text("""SELECT tablename FROM pg_tables
                                                WHERE tablename LIKE 'place_classtype_%'
                                             """))
            self._classtables = {r[0] for r in res}

        tablename = f"place_classtype_{cls}_{typ}"

        if tablename not in self._classtables:
            return None

        if tablename in self.t.meta.tables:
            return self.t.meta.tables[tablename]

        return sa.Table(tablename, self.t.meta,
                        sa.Column('place_id', sa.BigInteger),
                        sa.Column('centroid', Geometry))
