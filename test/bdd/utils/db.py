# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for managing test databases.
"""
import asyncio
import psycopg
from psycopg import sql as pysql

from nominatim_db.tools.database_import import setup_database_skeleton, create_tables, \
                                               create_partition_tables, create_search_indices
from nominatim_db.data.country_info import setup_country_tables
from nominatim_db.tools.refresh import create_functions, load_address_levels_from_config
from nominatim_db.tools.exec_utils import run_osm2pgsql
from nominatim_db.tokenizer import factory as tokenizer_factory


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

    def create_db_from_template(self, dbname, template):
        """ Create a new database from the given template database.
            Any existing database with the same name will be dropped.
        """
        with psycopg.connect(dbname='postgres') as conn:
            conn.autocommit = True
            conn.execute(pysql.SQL('DROP DATABASE IF EXISTS')
                         + pysql.Identifier(dbname))
            conn.execute(pysql.SQL('CREATE DATABASE {} WITH TEMPLATE {}')
                              .format(pysql.Identifier(dbname),
                                      pysql.Identifier(template)))

    def setup_template_db(self, config):
        """ Create a template DB which contains the necessary extensions
            and basic static tables.

            The template will only be created if the database does not yet
            exist or 'purge' is set.
        """
        dsn = config.get_libpq_dsn()

        if self.check_for_db(config.get_database_params()['dbname']):
            return

        setup_database_skeleton(dsn)

        run_osm2pgsql(dict(osm2pgsql='osm2pgsql',
                           osm2pgsql_cache=1,
                           osm2pgsql_style=str(config.get_import_style_file()),
                           osm2pgsql_style_path=config.lib_dir.lua,
                           threads=1,
                           dsn=dsn,
                           flatnode_file='',
                           tablespaces=dict(slim_data='', slim_index='',
                                            main_data='', main_index=''),
                           append=False,
                           import_data=b'<osm version="0.6"></osm>'))

        setup_country_tables(dsn, config.lib_dir.data)

        with psycopg.connect(dsn) as conn:
            create_tables(conn, config)
            load_address_levels_from_config(conn, config)
            create_partition_tables(conn, config)
            create_functions(conn, config, enable_diff_updates=False)
            asyncio.run(create_search_indices(conn, config))

        tokenizer_factory.create_tokenizer(config)
