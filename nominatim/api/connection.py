# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Extended SQLAlchemy connection class that also includes access to the schema.
"""
from typing import Any, Mapping, Sequence, Union

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

from nominatim.db.sqlalchemy_schema import SearchTables

class SearchConnection:
    """ An extended SQLAlchemy connection class, that also contains
        then table definitions. The underlying asynchronous SQLAlchemy
        connection can be accessed with the 'connection' property.
        The 't' property is the collection of Nominatim tables.
    """

    def __init__(self, conn: AsyncConnection,
                 tables: SearchTables) -> None:
        self.connection = conn
        self.t = tables # pylint: disable=invalid-name


    async def scalar(self, sql: sa.sql.base.Executable,
                     params: Union[Mapping[str, Any], None] = None
                    ) -> Any:
        """ Execute a 'scalar()' query on the connection.
        """
        return await self.connection.scalar(sql, params)


    async def execute(self, sql: sa.sql.base.Executable,
                      params: Union[Mapping[str, Any], Sequence[Mapping[str, Any]], None] = None
                     ) -> 'sa.engine.Result[Any]':
        """ Execute a 'execute()' query on the connection.
        """
        return await self.connection.execute(sql, params)
