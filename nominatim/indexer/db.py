# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim.
# Copyright (C) 2020 Sarah Hoffmann

import logging
import psycopg2
from psycopg2.extras import wait_select

log = logging.getLogger()

def make_connection(options, asynchronous=False):
    params = {'dbname' : options.dbname,
              'user' : options.user,
              'password' : options.password,
              'host' : options.host,
              'port' : options.port,
              'async' : asynchronous}

    return psycopg2.connect(**params)

class DBConnection(object):
    """ A single non-blocking database connection.
    """

    def __init__(self, options):
        self.current_query = None
        self.current_params = None
        self.options = options

        self.conn = None
        self.connect()

    def connect(self):
        """ (Re)connect to the database. Creates an asynchronous connection
            with JIT and parallel processing disabled. If a connection was
            already open, it is closed and a new connection established.
            The caller must ensure that no query is pending before reconnecting.
        """
        if self.conn is not None:
            self.cursor.close()
            self.conn.close()

        self.conn = make_connection(self.options, asynchronous=True)
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

    def wait(self):
        """ Block until any pending operation is done.
        """
        while True:
            try:
                wait_select(self.conn)
                self.current_query = None
                return
            except psycopg2.extensions.TransactionRollbackError as e:
                if e.pgcode == '40P01':
                    log.info("Deadlock detected (params = {}), retry."
                              .format(self.current_params))
                    self.cursor.execute(self.current_query, self.current_params)
                else:
                    raise
            except psycopg2.errors.DeadlockDetected:
                self.cursor.execute(self.current_query, self.current_params)

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

        try:
            if self.conn.poll() == psycopg2.extensions.POLL_OK:
                self.current_query = None
                return True
        except psycopg2.extensions.TransactionRollbackError as e:
            if e.pgcode == '40P01':
                log.info("Deadlock detected (params = {}), retry.".format(self.current_params))
                self.cursor.execute(self.current_query, self.current_params)
            else:
                raise
        except psycopg2.errors.DeadlockDetected:
            self.cursor.execute(self.current_query, self.current_params)

        return False

