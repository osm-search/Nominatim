"""
Specialised connection and cursor functions.
"""
import contextlib
import logging
import os

import psycopg2
import psycopg2.extensions
import psycopg2.extras

from ..errors import UsageError

LOG = logging.getLogger()

class _Cursor(psycopg2.extras.DictCursor):
    """ A cursor returning dict-like objects and providing specialised
        execution functions.
    """

    def execute(self, query, args=None): # pylint: disable=W0221
        """ Query execution that logs the SQL query when debugging is enabled.
        """
        LOG.debug(self.mogrify(query, args).decode('utf-8'))

        super().execute(query, args)

    def scalar(self, sql, args=None):
        """ Execute query that returns a single value. The value is returned.
            If the query yields more than one row, a ValueError is raised.
        """
        self.execute(sql, args)

        if self.rowcount != 1:
            raise RuntimeError("Query did not return a single row.")

        return self.fetchone()[0]


class _Connection(psycopg2.extensions.connection):
    """ A connection that provides the specialised cursor by default and
        adds convenience functions for administrating the database.
    """

    def cursor(self, cursor_factory=_Cursor, **kwargs):
        """ Return a new cursor. By default the specialised cursor is returned.
        """
        return super().cursor(cursor_factory=cursor_factory, **kwargs)


    def table_exists(self, table):
        """ Check that a table with the given name exists in the database.
        """
        with self.cursor() as cur:
            num = cur.scalar("""SELECT count(*) FROM pg_tables
                                WHERE tablename = %s and schemaname = 'public'""", (table, ))
            return num == 1


    def index_exists(self, index, table=None):
        """ Check that an index with the given name exists in the database.
            If table is not None then the index must relate to the given
            table.
        """
        with self.cursor() as cur:
            cur.execute("""SELECT tablename FROM pg_indexes
                           WHERE indexname = %s and schemaname = 'public'""", (index, ))
            if cur.rowcount == 0:
                return False

            if table is not None:
                row = cur.fetchone()
                return row[0] == table

        return True


    def server_version_tuple(self):
        """ Return the server version as a tuple of (major, minor).
            Converts correctly for pre-10 and post-10 PostgreSQL versions.
        """
        version = self.server_version
        if version < 100000:
            return (int(version / 10000), (version % 10000) / 100)

        return (int(version / 10000), version % 10000)


    def postgis_version_tuple(self):
        """ Return the postgis version installed in the database as a
            tuple of (major, minor). Assumes that the PostGIS extension
            has been installed already.
        """
        with self.cursor() as cur:
            version = cur.scalar('SELECT postgis_lib_version()')

        return tuple((int(x) for x in version.split('.')[:2]))


def connect(dsn):
    """ Open a connection to the database using the specialised connection
        factory. The returned object may be used in conjunction with 'with'.
        When used outside a context manager, use the `connection` attribute
        to get the connection.
    """
    try:
        conn = psycopg2.connect(dsn, connection_factory=_Connection)
        ctxmgr = contextlib.closing(conn)
        ctxmgr.connection = conn
        return ctxmgr
    except psycopg2.OperationalError as err:
        raise UsageError("Cannot connect to database: {}".format(err)) from err


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


def get_pg_env(dsn, base_env=None):
    """ Return a copy of `base_env` with the environment variables for
        PostgresSQL set up from the given database connection string.
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
