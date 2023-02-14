# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Extended SQLAlchemy connection class that also includes access to the schema.
"""
from typing import Any, Mapping, Sequence, Union, Dict, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from nominatim.db.sqlalchemy_schema import SearchTables
from nominatim.api.logging import log

class SearchConnection:
    """ An extended SQLAlchemy connection class, that also contains
        then table definitions. The underlying asynchronous SQLAlchemy
        connection can be accessed with the 'connection' property.
        The 't' property is the collection of Nominatim tables.
    """

    def __init__(self, conn: AsyncConnection,
                 tables: SearchTables,
                 properties: Dict[str, Any]) -> None:
        self.connection = conn
        self.t = tables # pylint: disable=invalid-name
        self._property_cache = properties


    async def scalar(self, sql: sa.sql.base.Executable,
                     params: Union[Mapping[str, Any], None] = None
                    ) -> Any:
        """ Execute a 'scalar()' query on the connection.
        """
        log().sql(self.connection, sql)
        return await self.connection.scalar(sql, params)


    async def execute(self, sql: 'sa.Executable',
                      params: Union[Mapping[str, Any], Sequence[Mapping[str, Any]], None] = None
                     ) -> 'sa.Result[Any]':
        """ Execute a 'execute()' query on the connection.
        """
        log().sql(self.connection, sql)
        return await self.connection.execute(sql, params)


    async def get_property(self, name: str, cached: bool = True) -> str:
        """ Get a property from Nominatim's property table.

            Property values are normally cached so that they are only
            retrieved from the database when they are queried for the
            first time with this function. Set 'cached' to False to force
            reading the property from the database.

            Raises a ValueError if the property does not exist.
        """
        if name.startswith('DB:'):
            raise ValueError(f"Illegal property value '{name}'.")

        if cached and name in self._property_cache:
            return cast(str, self._property_cache[name])

        sql = sa.select(self.t.properties.c.value)\
            .where(self.t.properties.c.property == name)
        value = await self.connection.scalar(sql)

        if value is None:
            raise ValueError(f"Property '{name}' not found in database.")

        self._property_cache[name] = cast(str, value)

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
