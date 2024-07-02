# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Specialised connection and cursor functions.
"""
from typing import Optional, Any, Callable, ContextManager, Dict, cast, overload,\
                   Tuple, Iterable
import contextlib
import logging
import os

import psycopg2
import psycopg2.extensions
import psycopg2.extras
from psycopg2 import sql as pysql

from ..typing import SysEnv, Query, T_cursor
from ..errors import UsageError

LOG = logging.getLogger()

class Cursor(psycopg2.extras.DictCursor):
    """ A cursor returning dict-like objects and providing specialised
        execution functions.
    """
    # pylint: disable=arguments-renamed,arguments-differ
    def execute(self, query: Query, args: Any = None) -> None:
        """ Query execution that logs the SQL query when debugging is enabled.
        """
        if LOG.isEnabledFor(logging.DEBUG):
            LOG.debug(self.mogrify(query, args).decode('utf-8'))

        super().execute(query, args)


    def execute_values(self, sql: Query, argslist: Iterable[Tuple[Any, ...]],
                       template: Optional[Query] = None) -> None:
        """ Wrapper for the psycopg2 convenience function to execute
            SQL for a list of values.
        """
        LOG.debug("SQL execute_values(%s, %s)", sql, argslist)

        psycopg2.extras.execute_values(self, sql, argslist, template=template)


class Connection(psycopg2.extensions.connection):
    """ A connection that provides the specialised cursor by default and
        adds convenience functions for administrating the database.
    """
    @overload # type: ignore[override]
    def cursor(self) -> Cursor:
        ...

    @overload
    def cursor(self, name: str) -> Cursor:
        ...

    @overload
    def cursor(self, cursor_factory: Callable[..., T_cursor]) -> T_cursor:
        ...

    def cursor(self, cursor_factory  = Cursor, **kwargs): # type: ignore
        """ Return a new cursor. By default the specialised cursor is returned.
        """
        return super().cursor(cursor_factory=cursor_factory, **kwargs)


def execute_scalar(conn: Connection, sql: Query, args: Any = None) -> Any:
    """ Execute query that returns a single value. The value is returned.
        If the query yields more than one row, a ValueError is raised.
    """
    with conn.cursor() as cur:
        cur.execute(sql, args)

        if cur.rowcount != 1:
            raise RuntimeError("Query did not return a single row.")

        result = cur.fetchone()

    assert result is not None
    return result[0]


def table_exists(conn: Connection, table: str) -> bool:
    """ Check that a table with the given name exists in the database.
    """
    num = execute_scalar(conn,
            """SELECT count(*) FROM pg_tables
               WHERE tablename = %s and schemaname = 'public'""", (table, ))
    return num == 1 if isinstance(num, int) else False


def table_has_column(conn: Connection, table: str, column: str) -> bool:
    """ Check if the table 'table' exists and has a column with name 'column'.
    """
    has_column = execute_scalar(conn,
                    """SELECT count(*) FROM information_schema.columns
                       WHERE table_name = %s and column_name = %s""",
                    (table, column))
    return has_column > 0 if isinstance(has_column, int) else False


def index_exists(conn: Connection, index: str, table: Optional[str] = None) -> bool:
    """ Check that an index with the given name exists in the database.
        If table is not None then the index must relate to the given
        table.
    """
    with conn.cursor() as cur:
        cur.execute("""SELECT tablename FROM pg_indexes
                       WHERE indexname = %s and schemaname = 'public'""", (index, ))
        if cur.rowcount == 0:
            return False

        if table is not None:
            row = cur.fetchone()
            if row is None or not isinstance(row[0], str):
                return False
            return row[0] == table

    return True

def drop_tables(conn: Connection, *names: str,
               if_exists: bool = True, cascade: bool = False) -> None:
    """ Drop one or more tables with the given names.
        Set `if_exists` to False if a non-existent table should raise
        an exception instead of just being ignored. `cascade` will cause
        depended objects to be dropped as well.
        The caller needs to take care of committing the change.
    """
    sql = pysql.SQL('DROP TABLE%s{}%s' % (
                        ' IF EXISTS ' if if_exists else ' ',
                        ' CASCADE' if cascade else ''))

    with conn.cursor() as cur:
        for name in names:
            cur.execute(sql.format(pysql.Identifier(name)))


def server_version_tuple(conn: Connection) -> Tuple[int, int]:
    """ Return the server version as a tuple of (major, minor).
        Converts correctly for pre-10 and post-10 PostgreSQL versions.
    """
    version = conn.server_version
    if version < 100000:
        return (int(version / 10000), int((version % 10000) / 100))

    return (int(version / 10000), version % 10000)


def postgis_version_tuple(conn: Connection) -> Tuple[int, int]:
    """ Return the postgis version installed in the database as a
        tuple of (major, minor). Assumes that the PostGIS extension
        has been installed already.
    """
    version = execute_scalar(conn, 'SELECT postgis_lib_version()')

    version_parts = version.split('.')
    if len(version_parts) < 2:
        raise UsageError(f"Error fetching Postgis version. Bad format: {version}")

    return (int(version_parts[0]), int(version_parts[1]))

def register_hstore(conn: Connection) -> None:
    """ Register the hstore type with psycopg for the connection.
    """
    psycopg2.extras.register_hstore(conn)


class ConnectionContext(ContextManager[Connection]):
    """ Context manager of the connection that also provides direct access
        to the underlying connection.
    """
    connection: Connection


def connect(dsn: str) -> ConnectionContext:
    """ Open a connection to the database using the specialised connection
        factory. The returned object may be used in conjunction with 'with'.
        When used outside a context manager, use the `connection` attribute
        to get the connection.
    """
    try:
        conn = psycopg2.connect(dsn, connection_factory=Connection)
        ctxmgr = cast(ConnectionContext, contextlib.closing(conn))
        ctxmgr.connection = conn
        return ctxmgr
    except psycopg2.OperationalError as err:
        raise UsageError(f"Cannot connect to database: {err}") from err


# Translation from PG connection string parameters to PG environment variables.
# Derived from https://www.postgresql.org/docs/current/libpq-envars.html.
_PG_CONNECTION_STRINGS = {
    'host': 'PGHOST',
    'hostaddr': 'PGHOSTADDR',
    'port': 'PGPORT',
    'dbname': 'PGDATABASE',
    'user': 'PGUSER',
    'password': 'PGPASSWORD',
    'passfile': 'PGPASSFILE',
    'channel_binding': 'PGCHANNELBINDING',
    'service': 'PGSERVICE',
    'options': 'PGOPTIONS',
    'application_name': 'PGAPPNAME',
    'sslmode': 'PGSSLMODE',
    'requiressl': 'PGREQUIRESSL',
    'sslcompression': 'PGSSLCOMPRESSION',
    'sslcert': 'PGSSLCERT',
    'sslkey': 'PGSSLKEY',
    'sslrootcert': 'PGSSLROOTCERT',
    'sslcrl': 'PGSSLCRL',
    'requirepeer': 'PGREQUIREPEER',
    'ssl_min_protocol_version': 'PGSSLMINPROTOCOLVERSION',
    'ssl_max_protocol_version': 'PGSSLMAXPROTOCOLVERSION',
    'gssencmode': 'PGGSSENCMODE',
    'krbsrvname': 'PGKRBSRVNAME',
    'gsslib': 'PGGSSLIB',
    'connect_timeout': 'PGCONNECT_TIMEOUT',
    'target_session_attrs': 'PGTARGETSESSIONATTRS',
}


def get_pg_env(dsn: str,
               base_env: Optional[SysEnv] = None) -> Dict[str, str]:
    """ Return a copy of `base_env` with the environment variables for
        PostgreSQL set up from the given database connection string.
        If `base_env` is None, then the OS environment is used as a base
        environment.
    """
    env = dict(base_env if base_env is not None else os.environ)

    for param, value in psycopg2.extensions.parse_dsn(dsn).items():
        if param in _PG_CONNECTION_STRINGS:
            env[_PG_CONNECTION_STRINGS[param]] = value
        else:
            LOG.error("Unknown connection parameter '%s' ignored.", param)

    return env
