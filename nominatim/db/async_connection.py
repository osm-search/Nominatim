# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim.
# Copyright (C) 2021 by the Nominatim developer community.
# For a full list of authors see the git log.
""" Database helper functions for the indexer.
"""
import logging
import psycopg2
from psycopg2.extras import wait_select

# psycopg2 emits different exceptions pre and post 2.8. Detect if the new error
# module is available and adapt the error handling accordingly.
try:
    import psycopg2.errors # pylint: disable=no-name-in-module,import-error
    __has_psycopg2_errors__ = True
except ModuleNotFoundError:
    __has_psycopg2_errors__ = False

LOG = logging.getLogger()

class DeadlockHandler:
    """ Context manager that catches deadlock exceptions and calls
        the given handler function. All other exceptions are passed on
        normally.
    """

    def __init__(self, handler):
        self.handler = handler

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        if __has_psycopg2_errors__:
            if exc_type == psycopg2.errors.DeadlockDetected: # pylint: disable=E1101
                self.handler()
                return True
        else:
            if exc_type == psycopg2.extensions.TransactionRollbackError:
                if exc_value.pgcode == '40P01':
                    self.handler()
                    return True
        return False


class DBConnection:
    """ A single non-blocking database connection.
    """

    def __init__(self, dsn):
        self.current_query = None
        self.current_params = None
        self.dsn = dsn

        self.conn = None
        self.cursor = None
        self.connect()

    def close(self):
        """ Close all open connections. Does not wait for pending requests.
        """
        if self.conn is not None:
            self.cursor.close()
            self.conn.close()

        self.conn = None

    def connect(self):
        """ (Re)connect to the database. Creates an asynchronous connection
            with JIT and parallel processing disabled. If a connection was
            already open, it is closed and a new connection established.
            The caller must ensure that no query is pending before reconnecting.
        """
        self.close()

        # Use a dict to hand in the parameters because async is a reserved
        # word in Python3.
        self.conn = psycopg2.connect(**{'dsn' : self.dsn, 'async' : True})
        self.wait()

        self.cursor = self.conn.cursor()
        # Disable JIT and parallel workers as they are known to cause problems.
        # Update pg_settings instead of using SET because it does not yield
        # errors on older versions of Postgres where the settings are not
        # implemented.
        self.perform(
            """ UPDATE pg_settings SET setting = -1 WHERE name = 'jit_above_cost';
                UPDATE pg_settings SET setting = 0
                   WHERE name = 'max_parallel_workers_per_gather';""")
        self.wait()

    def _deadlock_handler(self):
        LOG.info("Deadlock detected (params = %s), retry.", str(self.current_params))
        self.cursor.execute(self.current_query, self.current_params)

    def wait(self):
        """ Block until any pending operation is done.
        """
        while True:
            with DeadlockHandler(self._deadlock_handler):
                wait_select(self.conn)
                self.current_query = None
                return

    def perform(self, sql, args=None):
        """ Send SQL query to the server. Returns immediately without
            blocking.
        """
        self.current_query = sql
        self.current_params = args
        self.cursor.execute(sql, args)

    def fileno(self):
        """ File descriptor to wait for. (Makes this class select()able.)
        """
        return self.conn.fileno()

    def is_done(self):
        """ Check if the connection is available for a new query.

            Also checks if the previous query has run into a deadlock.
            If so, then the previous query is repeated.
        """
        if self.current_query is None:
            return True

        with DeadlockHandler(self._deadlock_handler):
            if self.conn.poll() == psycopg2.extensions.POLL_OK:
                self.current_query = None
                return True

        return False
