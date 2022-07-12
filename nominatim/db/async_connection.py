# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
""" Non-blocking database connections.
"""
from typing import Callable, Any, Optional, Iterator, Sequence
import logging
import select
import time

import psycopg2
from psycopg2.extras import wait_select

# psycopg2 emits different exceptions pre and post 2.8. Detect if the new error
# module is available and adapt the error handling accordingly.
try:
    import psycopg2.errors # pylint: disable=no-name-in-module,import-error
    __has_psycopg2_errors__ = True
except ImportError:
    __has_psycopg2_errors__ = False

from nominatim.typing import T_cursor, Query

LOG = logging.getLogger()

class DeadlockHandler:
    """ Context manager that catches deadlock exceptions and calls
        the given handler function. All other exceptions are passed on
        normally.
    """

    def __init__(self, handler: Callable[[], None], ignore_sql_errors: bool = False) -> None:
        self.handler = handler
        self.ignore_sql_errors = ignore_sql_errors

    def __enter__(self) -> 'DeadlockHandler':
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> bool:
        if __has_psycopg2_errors__:
            if exc_type == psycopg2.errors.DeadlockDetected: # pylint: disable=E1101
                self.handler()
                return True
        elif exc_type == psycopg2.extensions.TransactionRollbackError \
             and exc_value.pgcode == '40P01':
            self.handler()
            return True

        if self.ignore_sql_errors and isinstance(exc_value, psycopg2.Error):
            LOG.info("SQL error ignored: %s", exc_value)
            return True

        return False


class DBConnection:
    """ A single non-blocking database connection.
    """

    def __init__(self, dsn: str,
                 cursor_factory: Optional[Callable[..., T_cursor]] = None,
                 ignore_sql_errors: bool = False) -> None:
        self.dsn = dsn

        self.current_query: Optional[Query] = None
        self.current_params: Optional[Sequence[Any]] = None
        self.ignore_sql_errors = ignore_sql_errors

        self.conn: Optional['psycopg2.connection'] = None
        self.cursor: Optional['psycopg2.cursor'] = None
        self.connect(cursor_factory=cursor_factory)

    def close(self) -> None:
        """ Close all open connections. Does not wait for pending requests.
        """
        if self.conn is not None:
            if self.cursor is not None:
                self.cursor.close() # type: ignore[no-untyped-call]
                self.cursor = None
            self.conn.close()

        self.conn = None

    def connect(self, cursor_factory: Optional[Callable[..., T_cursor]] = None) -> None:
        """ (Re)connect to the database. Creates an asynchronous connection
            with JIT and parallel processing disabled. If a connection was
            already open, it is closed and a new connection established.
            The caller must ensure that no query is pending before reconnecting.
        """
        self.close()

        # Use a dict to hand in the parameters because async is a reserved
        # word in Python3.
        self.conn = psycopg2.connect(**{'dsn': self.dsn, 'async': True})
        self.wait()

        if cursor_factory is not None:
            self.cursor = self.conn.cursor(cursor_factory=cursor_factory)
        else:
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

    def _deadlock_handler(self) -> None:
        LOG.info("Deadlock detected (params = %s), retry.", str(self.current_params))
        assert self.cursor is not None
        assert self.current_query is not None
        assert self.current_params is not None

        self.cursor.execute(self.current_query, self.current_params)

    def wait(self) -> None:
        """ Block until any pending operation is done.
        """
        while True:
            with DeadlockHandler(self._deadlock_handler, self.ignore_sql_errors):
                wait_select(self.conn)
                self.current_query = None
                return

    def perform(self, sql: Query, args: Optional[Sequence[Any]] = None) -> None:
        """ Send SQL query to the server. Returns immediately without
            blocking.
        """
        assert self.cursor is not None
        self.current_query = sql
        self.current_params = args
        self.cursor.execute(sql, args)

    def fileno(self) -> int:
        """ File descriptor to wait for. (Makes this class select()able.)
        """
        assert self.conn is not None
        return self.conn.fileno()

    def is_done(self) -> bool:
        """ Check if the connection is available for a new query.

            Also checks if the previous query has run into a deadlock.
            If so, then the previous query is repeated.
        """
        assert self.conn is not None

        if self.current_query is None:
            return True

        with DeadlockHandler(self._deadlock_handler, self.ignore_sql_errors):
            if self.conn.poll() == psycopg2.extensions.POLL_OK:
                self.current_query = None
                return True

        return False


class WorkerPool:
    """ A pool of asynchronous database connections.

        The pool may be used as a context manager.
    """
    REOPEN_CONNECTIONS_AFTER = 100000

    def __init__(self, dsn: str, pool_size: int, ignore_sql_errors: bool = False) -> None:
        self.threads = [DBConnection(dsn, ignore_sql_errors=ignore_sql_errors)
                        for _ in range(pool_size)]
        self.free_workers = self._yield_free_worker()
        self.wait_time = 0.0


    def finish_all(self) -> None:
        """ Wait for all connection to finish.
        """
        for thread in self.threads:
            while not thread.is_done():
                thread.wait()

        self.free_workers = self._yield_free_worker()

    def close(self) -> None:
        """ Close all connections and clear the pool.
        """
        for thread in self.threads:
            thread.close()
        self.threads = []
        self.free_workers = iter([])


    def next_free_worker(self) -> DBConnection:
        """ Get the next free connection.
        """
        return next(self.free_workers)


    def _yield_free_worker(self) -> Iterator[DBConnection]:
        ready = self.threads
        command_stat = 0
        while True:
            for thread in ready:
                if thread.is_done():
                    command_stat += 1
                    yield thread

            if command_stat > self.REOPEN_CONNECTIONS_AFTER:
                self._reconnect_threads()
                ready = self.threads
                command_stat = 0
            else:
                tstart = time.time()
                _, ready, _ = select.select([], self.threads, [])
                self.wait_time += time.time() - tstart


    def _reconnect_threads(self) -> None:
        for thread in self.threads:
            while not thread.is_done():
                thread.wait()
            thread.connect()


    def __enter__(self) -> 'WorkerPool':
        return self


    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.finish_all()
        self.close()
