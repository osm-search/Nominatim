# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for managing test databases.
"""
import psycopg
from psycopg import sql as pysql


class DBManager:

    def __init__(self, purge=False):
        self.purge = purge

    def check_for_db(self, dbname):
        """ Check if the given DB already exists.
            When the purge option is set, then an existing database will
            be deleted and the function returns that it does not exist.
        """
        if self.purge:
            self.drop_db(dbname)
            return False

        return self.exists_db(dbname)

    def drop_db(self, dbname):
        """ Drop the given database if it exists.
        """
        with psycopg.connect(dbname='postgres') as conn:
            conn.autocommit = True
            conn.execute(pysql.SQL('DROP DATABASE IF EXISTS')
                         + pysql.Identifier(dbname))

    def exists_db(self, dbname):
        """ Check if a database with the given name exists already.
        """
        with psycopg.connect(dbname='postgres') as conn:
            cur = conn.execute('select count(*) from pg_database where datname = %s',
                               (dbname,))
            return cur.fetchone()[0] == 1
