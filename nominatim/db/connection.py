"""
Specialised connection and cursor functions.
"""
import logging

import psycopg2
import psycopg2.extensions
import psycopg2.extras

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
                                WHERE tablename = %s""", (table, ))
            return num == 1


def connect(dsn):
    """ Open a connection to the database using the specialised connection
        factory.
    """
    return psycopg2.connect(dsn, connection_factory=_Connection)
