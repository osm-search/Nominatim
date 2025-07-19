# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for bringing auxiliary data in the database up-to-date.
"""
from typing import MutableSequence, Tuple, Any, Mapping, Sequence, List
import csv
import gzip
import logging
from pathlib import Path

from psycopg import sql as pysql

from ..config import Configuration
from ..db.connection import Connection, connect, drop_tables
from ..db.utils import execute_file
from ..db.sql_preprocessor import SQLPreprocessor

LOG = logging.getLogger()

OSM_TYPE = {'N': 'node', 'W': 'way', 'R': 'relation'}


def _add_address_level_rows_from_entry(rows: MutableSequence[Tuple[Any, ...]],
                                       entry: Mapping[str, Any]) -> None:
    """ Converts a single entry from the JSON format for address rank
        descriptions into a flat format suitable for inserting into a
        PostgreSQL table and adds these lines to `rows`.
    """
    countries = entry.get('countries') or (None, )
    for key, values in entry['tags'].items():
        for value, ranks in values.items():
            if isinstance(ranks, list):
                rank_search, rank_address = ranks
            else:
                rank_search = rank_address = ranks
            if not value:
                value = None
            for country in countries:
                rows.append((country, key, value, rank_search, rank_address))


def load_address_levels(conn: Connection, table: str, levels: Sequence[Mapping[str, Any]]) -> None:
    """ Replace the `address_levels` table with the contents of `levels'.

        A new table is created any previously existing table is dropped.
        The table has the following columns:
            country, class, type, rank_search, rank_address
    """
    rows: List[Tuple[Any, ...]] = []
    for entry in levels:
        _add_address_level_rows_from_entry(rows, entry)

    drop_tables(conn, table)

    with conn.cursor() as cur:
        cur.execute(pysql.SQL("""CREATE TABLE {} (
                                        country_code varchar(2),
                                        class TEXT,
                                        type TEXT,
                                        rank_search SMALLINT,
                                        rank_address SMALLINT)
                              """).format(pysql.Identifier(table)))

        cur.executemany(pysql.SQL("INSERT INTO {} VALUES (%s, %s, %s, %s, %s)")
                             .format(pysql.Identifier(table)), rows)

        cur.execute(pysql.SQL('CREATE UNIQUE INDEX ON {} (country_code, class, type)')
                    .format(pysql.Identifier(table)))

    conn.commit()


def load_address_levels_from_config(conn: Connection, config: Configuration) -> None:
    """ Replace the `address_levels` table with the content as
        defined in the given configuration. Uses the parameter
        NOMINATIM_ADDRESS_LEVEL_CONFIG to determine the location of the
        configuration file.
    """
    cfg = config.load_sub_configuration('', config='ADDRESS_LEVEL_CONFIG')
    load_address_levels(conn, 'address_levels', cfg)


def create_functions(conn: Connection, config: Configuration,
                     enable_diff_updates: bool = True,
                     enable_debug: bool = False) -> None:
    """ (Re)create the PL/pgSQL functions.
    """
    sql = SQLPreprocessor(conn, config)

    sql.run_sql_file(conn, 'functions.sql',
                     disable_diff_updates=not enable_diff_updates,
                     debug=enable_debug)


def import_wikipedia_articles(dsn: str, data_path: Path, ignore_errors: bool = False) -> int:
    """ Replaces the wikipedia importance tables with new data.
        The import is run in a single transaction so that the new data
        is replace seamlessly.

        Returns 0 if all was well and 1 if the importance file could not
        be found. Throws an exception if there was an error reading the file.
    """
    if import_importance_csv(dsn, data_path / 'wikimedia-importance.csv.gz') == 0 \
       or import_importance_sql(dsn, data_path / 'wikimedia-importance.sql.gz',
                                ignore_errors) == 0:
        return 0

    return 1


def import_importance_csv(dsn: str, data_file: Path) -> int:
    """ Replace wikipedia importance table with data from a
        single CSV file.

        The file must be a gzipped CSV and have the following columns:
        language, title, importance, wikidata_id

        Other columns may be present but will be ignored.
    """
    if not data_file.exists():
        return 1

    # Only import the first occurrence of a wikidata ID.
    # This keeps indexes and table small.
    wd_done = set()

    with connect(dsn) as conn:
        drop_tables(conn, 'wikipedia_article', 'wikipedia_redirect', 'wikimedia_importance')
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE wikimedia_importance (
                             language TEXT NOT NULL,
                             title TEXT NOT NULL,
                             importance double precision NOT NULL,
                             wikidata TEXT
                           ) """)

            copy_cmd = """COPY wikimedia_importance(language, title, importance, wikidata)
                          FROM STDIN"""
            with gzip.open(str(data_file), 'rt') as fd, cur.copy(copy_cmd) as copy:
                for row in csv.DictReader(fd, delimiter='\t', quotechar='|'):
                    wd_id = int(row['wikidata_id'][1:])
                    copy.write_row((row['language'],
                                    row['title'],
                                    row['importance'],
                                    None if wd_id in wd_done else row['wikidata_id']))
                    wd_done.add(wd_id)

            cur.execute("""CREATE INDEX IF NOT EXISTS idx_wikimedia_importance_title
                           ON wikimedia_importance (title)""")
            cur.execute("""CREATE INDEX IF NOT EXISTS idx_wikimedia_importance_wikidata
                           ON wikimedia_importance (wikidata)
                           WHERE wikidata is not null""")

        conn.commit()

    return 0


def import_importance_sql(dsn: str, data_file: Path, ignore_errors: bool) -> int:
    """ Replace wikipedia importance table with data from an SQL file.
    """
    if not data_file.exists():
        return 1

    pre_code = """BEGIN;
                  DROP TABLE IF EXISTS "wikipedia_article";
                  DROP TABLE IF EXISTS "wikipedia_redirect";
                  DROP TABLE IF EXISTS "wikipedia_importance";
               """
    post_code = "COMMIT"
    execute_file(dsn, data_file, ignore_errors=ignore_errors,
                 pre_code=pre_code, post_code=post_code)

    return 0


def import_secondary_importance(dsn: str, data_path: Path, ignore_errors: bool = False) -> int:
    """ Replaces the secondary importance raster data table with new data.

        Returns 0 if all was well and 1 if the raster SQL file could not
        be found. Throws an exception if there was an error reading the file.
    """
    datafile = data_path / 'secondary_importance.sql.gz'
    if not datafile.exists():
        return 1

    execute_file(dsn, datafile, ignore_errors=ignore_errors)

    return 0


def recompute_importance(conn: Connection) -> None:
    """ Recompute wikipedia links and importance for all entries in placex.
        This is a long-running operations that must not be executed in
        parallel with updates.
    """
    with conn.cursor() as cur:
        cur.execute('ALTER TABLE placex DISABLE TRIGGER ALL')
        cur.execute("""
            UPDATE placex SET (wikipedia, importance) =
               (SELECT wikipedia, importance
                FROM compute_importance(extratags, country_code, rank_search, centroid))
            """)
        cur.execute("""
            UPDATE placex s SET wikipedia = d.wikipedia, importance = d.importance
             FROM placex d
             WHERE s.place_id = d.linked_place_id and d.wikipedia is not null
                   and (s.wikipedia is null or s.importance < d.importance);
            """)
        cur.execute("""
            UPDATE search_name s SET importance = p.importance
             FROM placex p
             WHERE s.place_id = p.place_id AND s.importance != p.importance
            """)

        cur.execute('ALTER TABLE placex ENABLE TRIGGER ALL')
    conn.commit()


def invalidate_osm_object(osm_type: str, osm_id: int, conn: Connection,
                          recursive: bool = True) -> None:
    """ Mark the given OSM object for reindexing. When 'recursive' is set
        to True (the default), then all dependent objects are marked for
        reindexing as well.

        'osm_type' must be on of 'N' (node), 'W' (way) or 'R' (relation).
        If the given object does not exist, then nothing happens.
    """
    assert osm_type in ('N', 'R', 'W')

    LOG.warning("Invalidating OSM %s %s%s.",
                OSM_TYPE[osm_type], osm_id,
                ' and its dependent places' if recursive else '')

    with conn.cursor() as cur:
        if recursive:
            sql = """SELECT place_force_update(place_id)
                     FROM placex WHERE osm_type = %s and osm_id = %s"""
        else:
            sql = """UPDATE placex SET indexed_status = 2
                     WHERE osm_type = %s and osm_id = %s"""

        cur.execute(sql, (osm_type, osm_id))
