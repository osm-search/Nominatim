# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tokenizer implementing normalisation as used before Nominatim 4 but using
libICU instead of the PostgreSQL module.
"""
from typing import Optional
import logging

from psycopg import sql as pysql

from ...db.connection import connect, Connection, drop_tables, table_exists
from ...config import Configuration
from ...db.sql_preprocessor import SQLPreprocessor
from ..base import AbstractTokenizer
from .analyzer import ICUNameAnalyzer
from .rule_loader import ICURuleLoader
from . import icu_types as itype

LOG = logging.getLogger()


class ICUTokenizer(AbstractTokenizer):
    """ This tokenizer uses libICU to convert names and queries to ASCII.
        Otherwise it uses the same algorithms and data structures as the
        normalization routines in Nominatim 3.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn
        self.loader: Optional[ICURuleLoader] = None

    def init_new_db(self, config: Configuration, init_db: bool = True) -> None:
        """ Set up a new tokenizer for the database.

            This copies all necessary data in the project directory to make
            sure the tokenizer remains stable even over updates.
        """
        self.loader = ICURuleLoader(config)

        self._save_config()

        if init_db:
            self.update_sql_functions(config)
            self._setup_db_tables(config)
            self._create_base_indices(config, 'word')

    def init_from_project(self, config: Configuration) -> None:
        """ Initialise the tokenizer from the project directory.
        """
        self.loader = ICURuleLoader(config)

        with connect(self.dsn) as conn:
            self.loader.load_config_from_db(conn)

    def finalize_import(self, config: Configuration, threads: int = 2) -> None:
        """ Do any required postprocessing to make the tokenizer data ready
            for use.
        """
        with connect(self.dsn) as conn:
            reverse_only = not table_exists(conn, 'search_name')

        if reverse_only:
            self._create_lookup_indices(config, 'word')
        else:
            self.update_statistics(config, threads)

    def update_sql_functions(self, config: Configuration) -> None:
        """ Reimport the SQL functions for this tokenizer.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/icu_tokenizer.sql')

    def check_database(self, config: Configuration) -> None:
        """ Check that the tokenizer is set up correctly.
        """
        # Will throw an error if there is an issue.
        self.init_from_project(config)

    def update_statistics(self, config: Configuration, threads: int = 2) -> None:
        """ Recompute frequencies for all name words.
        """
        with connect(self.dsn) as conn:
            if not table_exists(conn, 'search_name'):
                return

            with conn.cursor() as cur:
                cur.execute('ANALYSE search_name')
                if threads > 1:
                    cur.execute(pysql.SQL('SET max_parallel_workers_per_gather TO {}')
                                     .format(pysql.Literal(min(threads, 6),)))

                LOG.info('Computing word frequencies')
                drop_tables(conn, 'word_frequencies')
                cur.execute("""
                  CREATE TEMP TABLE word_frequencies AS
                  WITH word_freq AS MATERIALIZED (
                           SELECT unnest(name_vector) as id, count(*)
                                 FROM search_name GROUP BY id),
                       addr_freq AS MATERIALIZED (
                           SELECT unnest(nameaddress_vector) as id, count(*)
                                 FROM search_name GROUP BY id)
                  SELECT coalesce(a.id, w.id) as id,
                         (CASE WHEN w.count is null or w.count <= 1 THEN '{}'::JSONB
                              ELSE jsonb_build_object('count', w.count) END
                          ||
                          CASE WHEN a.count is null or a.count <= 1 THEN '{}'::JSONB
                              ELSE jsonb_build_object('addr_count', a.count) END) as info
                  FROM word_freq w FULL JOIN addr_freq a ON a.id = w.id;
                  """)
                cur.execute('CREATE UNIQUE INDEX ON word_frequencies(id) INCLUDE(info)')
                cur.execute('ANALYSE word_frequencies')
                LOG.info('Update word table with recomputed frequencies')
                drop_tables(conn, 'tmp_word')
                cur.execute("CREATE TABLE tmp_word (LIKE word)")
                cur.execute("""INSERT INTO tmp_word
                                SELECT word_id, word_token, type, word,
                                       coalesce(word.info, '{}'::jsonb)
                                       - 'count' - 'addr_count' ||
                                       coalesce(wf.info, '{}'::jsonb)
                                       as info
                                FROM word LEFT JOIN word_frequencies wf
                                     ON word.word_id = wf.id
                            """)
                drop_tables(conn, 'word_frequencies')

            with conn.cursor() as cur:
                cur.execute('SET max_parallel_workers_per_gather TO 0')

            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_string(conn,
                            'GRANT SELECT ON tmp_word TO "{{config.DATABASE_WEBUSER}}"')
            conn.commit()
        self._create_base_indices(config, 'tmp_word')
        self._create_lookup_indices(config, 'tmp_word')
        self._move_temporary_word_table('tmp_word')

    def _cleanup_housenumbers(self) -> None:
        """ Remove unused house numbers.
        """
        with connect(self.dsn) as conn:
            if not table_exists(conn, 'search_name'):
                return
            with conn.cursor(name="hnr_counter") as cur:
                cur.execute("""SELECT DISTINCT word_id, coalesce(info->>'lookup', word_token)
                               FROM word
                               WHERE type = 'H'
                                 AND NOT EXISTS(SELECT * FROM search_name
                                                WHERE ARRAY[word.word_id] && name_vector)
                                 AND (char_length(coalesce(word, word_token)) > 6
                                      OR coalesce(word, word_token) not similar to '\\d+')
                            """)
                candidates = {token: wid for wid, token in cur}
            with conn.cursor(name="hnr_counter") as cur:
                cur.execute("""SELECT housenumber FROM placex
                               WHERE housenumber is not null
                                     AND (char_length(housenumber) > 6
                                          OR housenumber not similar to '\\d+')
                            """)
                for row in cur:
                    for hnr in row[0].split(';'):
                        candidates.pop(hnr, None)
            LOG.info("There are %s outdated housenumbers.", len(candidates))
            LOG.debug("Outdated housenumbers: %s", candidates.keys())
            if candidates:
                with conn.cursor() as cur:
                    cur.execute("""DELETE FROM word WHERE word_id = any(%s)""",
                                (list(candidates.values()), ))
                conn.commit()

    def update_word_tokens(self) -> None:
        """ Remove unused tokens.
        """
        LOG.warning("Cleaning up housenumber tokens.")
        self._cleanup_housenumbers()
        LOG.warning("Tokenizer house-keeping done.")

    def name_analyzer(self) -> 'ICUNameAnalyzer':
        """ Create a new analyzer for tokenizing names and queries
            using this tokinzer. Analyzers are context managers and should
            be used accordingly:

            ```
            with tokenizer.name_analyzer() as analyzer:
                analyser.tokenize()
            ```

            When used outside the with construct, the caller must ensure to
            call the close() function before destructing the analyzer.

            Analyzers are not thread-safe. You need to instantiate one per thread.
        """
        assert self.loader is not None
        return ICUNameAnalyzer(self.dsn, self.loader.make_token_analysis())

    def most_frequent_words(self, conn: Connection, num: int) -> list[str]:
        """ Return a list of the `num` most frequent full words
            in the database.
        """
        with conn.cursor() as cur:
            cur.execute("""SELECT word, sum((info->>'count')::int) as count
                             FROM word WHERE type = 'W'
                             GROUP BY word
                             ORDER BY count DESC LIMIT %s""", (num,))
            return list(s[0].split('@')[0] for s in cur)

    def _save_config(self) -> None:
        """ Save the configuration that needs to remain stable for the given
            database as database properties.
        """
        assert self.loader is not None
        with connect(self.dsn) as conn:
            self.loader.save_config_to_db(conn)

    def _setup_db_tables(self, config: Configuration) -> None:
        """ Set up the word table and fill it with pre-computed word
            frequencies.
        """
        with connect(self.dsn) as conn:
            drop_tables(conn, 'word')
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_string(conn, """
                CREATE TABLE word (
                      word_id INTEGER,
                      word_token text NOT NULL,
                      type text NOT NULL,
                      word text,
                      info jsonb
                    ) {{db.tablespace.search_data}};
                GRANT SELECT ON word TO "{{config.DATABASE_WEBUSER}}";

                DROP SEQUENCE IF EXISTS seq_word;
                CREATE SEQUENCE seq_word start 1;
                GRANT SELECT ON seq_word to "{{config.DATABASE_WEBUSER}}";
            """)
            conn.commit()

    def _create_base_indices(self, config: Configuration, table_name: str) -> None:
        """ Set up the word table and fill it with pre-computed word
            frequencies.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_string(conn,
                            """CREATE INDEX idx_{{table_name}}_word_token ON {{table_name}}
                               USING BTREE (word_token) {{db.tablespace.search_index}}""",
                            table_name=table_name)
            for name, ctype in itype.WORD_TYPES:
                sqlp.run_string(conn,
                                """CREATE INDEX idx_{{table_name}}_{{idx_name}} ON {{table_name}}
                                   USING BTREE (word) {{db.tablespace.address_index}}
                                   WHERE type = '{{column_type}}'
                                """,
                                table_name=table_name, idx_name=name,
                                column_type=ctype)
            conn.commit()

    def _create_lookup_indices(self, config: Configuration, table_name: str) -> None:
        """ Create additional indexes used when running the API.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            # Index required for details lookup.
            sqlp.run_string(
                conn,
                """
                CREATE INDEX IF NOT EXISTS idx_{{table_name}}_word_id
                  ON {{table_name}} USING BTREE (word_id) {{db.tablespace.search_index}}
                """,
                table_name=table_name)
            conn.commit()

    def _move_temporary_word_table(self, old: str) -> None:
        """ Rename all tables and indexes used by the tokenizer.
        """
        with connect(self.dsn) as conn:
            drop_tables(conn, 'word')
            with conn.cursor() as cur:
                cur.execute(pysql.SQL("ALTER TABLE {} RENAME TO word")
                                 .format(pysql.Identifier(old)))
                for idx in ['word_token', 'word_id'] + [n[0] for n in itype.WORD_TYPES]:
                    cur.execute(pysql.SQL("ALTER INDEX {} RENAME TO {}")
                                     .format(pysql.Identifier(f"idx_{old}_{idx}"),
                                             pysql.Identifier(f"idx_word_{idx}")))
            conn.commit()


def create(dsn: str) -> ICUTokenizer:
    """ Create a new instance of the tokenizer provided by this module.
    """
    return ICUTokenizer(dsn)
