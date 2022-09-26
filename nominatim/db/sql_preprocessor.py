# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Preprocessing of SQL files.
"""
from typing import Set, Dict, Any
import jinja2

from nominatim.db.connection import Connection
from nominatim.db.async_connection import WorkerPool
from nominatim.config import Configuration

def _get_partitions(conn: Connection) -> Set[int]:
    """ Get the set of partitions currently in use.
    """
    with conn.cursor() as cur:
        cur.execute('SELECT DISTINCT partition FROM country_name')
        partitions = set([0])
        for row in cur:
            partitions.add(row[0])

    return partitions


def _get_tables(conn: Connection) -> Set[str]:
    """ Return the set of tables currently in use.
        Only includes non-partitioned
    """
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")

        return set((row[0] for row in list(cur)))


def _setup_tablespace_sql(config: Configuration) -> Dict[str, str]:
    """ Returns a dict with tablespace expressions for the different tablespace
        kinds depending on whether a tablespace is configured or not.
    """
    out = {}
    for subset in ('ADDRESS', 'SEARCH', 'AUX'):
        for kind in ('DATA', 'INDEX'):
            tspace = getattr(config, f'TABLESPACE_{subset}_{kind}')
            if tspace:
                tspace = f'TABLESPACE "{tspace}"'
            out[f'{subset.lower()}_{kind.lower()}'] = tspace

    return out


def _setup_postgresql_features(conn: Connection) -> Dict[str, Any]:
    """ Set up a dictionary with various optional Postgresql/Postgis features that
        depend on the database version.
    """
    pg_version = conn.server_version_tuple()
    postgis_version = conn.postgis_version_tuple()
    return {
        'has_index_non_key_column': pg_version >= (11, 0, 0),
        'spgist_geom' : 'SPGIST' if postgis_version >= (3, 0) else 'GIST'
    }

class SQLPreprocessor:
    """ A environment for preprocessing SQL files from the
        lib-sql directory.

        The preprocessor provides a number of default filters and variables.
        The variables may be overwritten when rendering an SQL file.

        The preprocessing is currently based on the jinja2 templating library
        and follows its syntax.
    """

    def __init__(self, conn: Connection, config: Configuration) -> None:
        self.env = jinja2.Environment(autoescape=False,
                                      loader=jinja2.FileSystemLoader(str(config.lib_dir.sql)))

        db_info: Dict[str, Any] = {}
        db_info['partitions'] = _get_partitions(conn)
        db_info['tables'] = _get_tables(conn)
        db_info['reverse_only'] = 'search_name' not in db_info['tables']
        db_info['tablespace'] = _setup_tablespace_sql(config)

        self.env.globals['config'] = config
        self.env.globals['db'] = db_info
        self.env.globals['postgres'] = _setup_postgresql_features(conn)


    def run_sql_file(self, conn: Connection, name: str, **kwargs: Any) -> None:
        """ Execute the given SQL file on the connection. The keyword arguments
            may supply additional parameters for preprocessing.
        """
        sql = self.env.get_template(name).render(**kwargs)

        with conn.cursor() as cur:
            cur.execute(sql)
        conn.commit()


    def run_parallel_sql_file(self, dsn: str, name: str, num_threads: int = 1,
                              **kwargs: Any) -> None:
        """ Execure the given SQL files using parallel asynchronous connections.
            The keyword arguments may supply additional parameters for
            preprocessing.

            After preprocessing the SQL code is cut at lines containing only
            '---'. Each chunk is sent to one of the `num_threads` workers.
        """
        sql = self.env.get_template(name).render(**kwargs)

        parts = sql.split('\n---\n')

        with WorkerPool(dsn, num_threads) as pool:
            for part in parts:
                pool.next_free_worker().perform(part)
