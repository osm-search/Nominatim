"""
Specialised connection and cursor functions.
"""
import logging

import psycopg2
import psycopg2.extensions
import psycopg2.extras

from ..errors import UsageError

class _Cursor(psycopg2.extras.DictCursor):
    """ A cursor returning dict-like objects and providing specialised
        execution functions.
    """

    def execute(self, query, args=None): # pylint: disable=W0221
        """ Query execution that logs the SQL query when debugging is enabled.
        """
        logger = logging.getLogger()
        logger.debug(self.mogrify(query, args).decode('utf-8'))

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
            return (version / 10000, (version % 10000) / 100)

        return (version / 10000, version % 10000)

def connect(dsn):
    """ Open a connection to the database using the specialised connection
        factory.
    """
    try:
        return psycopg2.connect(dsn, connection_factory=_Connection)
    except psycopg2.OperationalError as err:
        raise UsageError("Cannot connect to database: {}".format(err)) from err
