# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tokenizer implementing normalisation as used before Nominatim 4 but using
libICU instead of the PostgreSQL module.
"""
from typing import Optional, Sequence, List, Tuple, Mapping, Any, cast, \
                   Dict, Set, Iterable
import itertools
import logging

from psycopg.types.json import Jsonb
from psycopg import sql as pysql

from ..db.connection import connect, Connection, Cursor, \
                            drop_tables, table_exists, execute_scalar
from ..config import Configuration
from ..db.sql_preprocessor import SQLPreprocessor
from ..data.place_info import PlaceInfo
from ..data.place_name import PlaceName
from .icu_rule_loader import ICURuleLoader
from .place_sanitizer import PlaceSanitizer
from .icu_token_analysis import ICUTokenAnalysis
from .base import AbstractAnalyzer, AbstractTokenizer

DBCFG_TERM_NORMALIZATION = "tokenizer_term_normalization"

LOG = logging.getLogger()

WORD_TYPES = (('country_names', 'C'),
              ('postcodes', 'P'),
              ('full_word', 'W'),
              ('housenumbers', 'H'))


def create(dsn: str) -> 'ICUTokenizer':
    """ Create a new instance of the tokenizer provided by this module.
    """
    return ICUTokenizer(dsn)


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

    def finalize_import(self, config: Configuration) -> None:
        """ Do any required postprocessing to make the tokenizer data ready
            for use.
        """
        self._create_lookup_indices(config, 'word')

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
                cur.execute("""CREATE TABLE tmp_word AS
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
        return ICUNameAnalyzer(self.dsn, self.loader.make_sanitizer(),
                               self.loader.make_token_analysis())

    def most_frequent_words(self, conn: Connection, num: int) -> List[str]:
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

                DROP SEQUENCE IF EXISTS seq_word;
                CREATE SEQUENCE seq_word start 1;
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
            for name, ctype in WORD_TYPES:
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
                cur.execute(f"ALTER TABLE {old} RENAME TO word")
                for idx in ('word_token', 'word_id'):
                    cur.execute(f"""ALTER INDEX idx_{old}_{idx}
                                      RENAME TO idx_word_{idx}""")
                for name, _ in WORD_TYPES:
                    cur.execute(f"""ALTER INDEX idx_{old}_{name}
                                    RENAME TO idx_word_{name}""")
            conn.commit()


class ICUNameAnalyzer(AbstractAnalyzer):
    """ The ICU analyzer uses the ICU library for splitting names.

        Each instance opens a connection to the database to request the
        normalization.
    """

    def __init__(self, dsn: str, sanitizer: PlaceSanitizer,
                 token_analysis: ICUTokenAnalysis) -> None:
        self.conn: Optional[Connection] = connect(dsn)
        self.conn.autocommit = True
        self.sanitizer = sanitizer
        self.token_analysis = token_analysis

        self._cache = _TokenCache()

    def close(self) -> None:
        """ Free all resources used by the analyzer.
        """
        if self.conn:
            self.conn.close()
            self.conn = None

    def _search_normalized(self, name: str) -> str:
        """ Return the search token transliteration of the given name.
        """
        return cast(str, self.token_analysis.search.transliterate(name)).strip()

    def _normalized(self, name: str) -> str:
        """ Return the normalized version of the given name with all
            non-relevant information removed.
        """
        return cast(str, self.token_analysis.normalizer.transliterate(name)).strip()

    def get_word_token_info(self, words: Sequence[str]) -> List[Tuple[str, str, Optional[int]]]:
        """ Return token information for the given list of words.
            If a word starts with # it is assumed to be a full name
            otherwise is a partial name.

            The function returns a list of tuples with
            (original word, word token, word id).

            The function is used for testing and debugging only
            and not necessarily efficient.
        """
        assert self.conn is not None
        full_tokens = {}
        partial_tokens = {}
        for word in words:
            if word.startswith('#'):
                full_tokens[word] = self._search_normalized(word[1:])
            else:
                partial_tokens[word] = self._search_normalized(word)

        with self.conn.cursor() as cur:
            cur.execute("""SELECT word_token, word_id
                            FROM word WHERE word_token = ANY(%s) and type = 'W'
                        """, (list(full_tokens.values()),))
            full_ids = {r[0]: cast(int, r[1]) for r in cur}
            cur.execute("""SELECT word_token, word_id
                            FROM word WHERE word_token = ANY(%s) and type = 'w'""",
                        (list(partial_tokens.values()),))
            part_ids = {r[0]: cast(int, r[1]) for r in cur}

        return [(k, v, full_ids.get(v, None)) for k, v in full_tokens.items()] \
            + [(k, v, part_ids.get(v, None)) for k, v in partial_tokens.items()]

    def normalize_postcode(self, postcode: str) -> str:
        """ Convert the postcode to a standardized form.

            This function must yield exactly the same result as the SQL function
            'token_normalized_postcode()'.
        """
        return postcode.strip().upper()

    def update_postcodes_from_db(self) -> None:
        """ Postcode update.

            Removes all postcodes from the word table because they are not
            needed. Postcodes are recognised by pattern.
        """
        assert self.conn is not None

        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM word WHERE type = 'P'")

    def update_special_phrases(self, phrases: Iterable[Tuple[str, str, str, str]],
                               should_replace: bool) -> None:
        """ Replace the search index for special phrases with the new phrases.
            If `should_replace` is True, then the previous set of will be
            completely replaced. Otherwise the phrases are added to the
            already existing ones.
        """
        assert self.conn is not None
        norm_phrases = set(((self._normalized(p[0]), p[1], p[2], p[3])
                            for p in phrases))

        with self.conn.cursor() as cur:
            # Get the old phrases.
            existing_phrases = set()
            cur.execute("SELECT word, info FROM word WHERE type = 'S'")
            for word, info in cur:
                existing_phrases.add((word, info['class'], info['type'],
                                      info.get('op') or '-'))

            added = self._add_special_phrases(cur, norm_phrases, existing_phrases)
            if should_replace:
                deleted = self._remove_special_phrases(cur, norm_phrases,
                                                       existing_phrases)
            else:
                deleted = 0

        LOG.info("Total phrases: %s. Added: %s. Deleted: %s",
                 len(norm_phrases), added, deleted)

    def _add_special_phrases(self, cursor: Cursor,
                             new_phrases: Set[Tuple[str, str, str, str]],
                             existing_phrases: Set[Tuple[str, str, str, str]]) -> int:
        """ Add all phrases to the database that are not yet there.
        """
        to_add = new_phrases - existing_phrases

        added = 0
        with cursor.copy('COPY word(word_token, type, word, info) FROM STDIN') as copy:
            for word, cls, typ, oper in to_add:
                term = self._search_normalized(word)
                if term:
                    copy.write_row((term, 'S', word,
                                    Jsonb({'class': cls, 'type': typ,
                                           'op': oper if oper in ('in', 'near') else None})))
                    added += 1

        return added

    def _remove_special_phrases(self, cursor: Cursor,
                                new_phrases: Set[Tuple[str, str, str, str]],
                                existing_phrases: Set[Tuple[str, str, str, str]]) -> int:
        """ Remove all phrases from the database that are no longer in the
            new phrase list.
        """
        to_delete = existing_phrases - new_phrases

        if to_delete:
            cursor.executemany(
                """ DELETE FROM word
                      WHERE type = 'S' and word = %s
                            and info->>'class' = %s and info->>'type' = %s
                            and %s = coalesce(info->>'op', '-')
                """, to_delete)

        return len(to_delete)

    def add_country_names(self, country_code: str, names: Mapping[str, str]) -> None:
        """ Add default names for the given country to the search index.
        """
        # Make sure any name preprocessing for country names applies.
        info = PlaceInfo({'name': names, 'country_code': country_code,
                          'rank_address': 4, 'class': 'boundary',
                          'type': 'administrative'})
        self._add_country_full_names(country_code,
                                     self.sanitizer.process_names(info)[0],
                                     internal=True)

    def _add_country_full_names(self, country_code: str, names: Sequence[PlaceName],
                                internal: bool = False) -> None:
        """ Add names for the given country from an already sanitized
            name list.
        """
        assert self.conn is not None
        word_tokens = set()
        for name in names:
            norm_name = self._normalized(name.name)
            token_name = self._search_normalized(name.name)
            if norm_name and token_name:
                word_tokens.add((token_name, norm_name))

        with self.conn.cursor() as cur:
            # Get existing names
            cur.execute("""SELECT word_token,
                                  word as lookup,
                                  coalesce(info ? 'internal', false) as is_internal
                             FROM word
                             WHERE type = 'C' and info->>'cc' = %s""",
                        (country_code, ))
            # internal/external names
            existing_tokens: Dict[bool, Set[Tuple[str, str]]] = {True: set(), False: set()}
            for word in cur:
                existing_tokens[word[2]].add((word[0], word[1]))

            # Delete names that no longer exist.
            gone_tokens = existing_tokens[internal] - word_tokens
            if internal:
                gone_tokens.update(existing_tokens[False] & word_tokens)
            if gone_tokens:
                cur.execute("""DELETE FROM word
                               USING jsonb_array_elements(%s) as data
                               WHERE type = 'C' and info->>'cc' = %s
                                     and word_token = data->>0 and word = data->>1""",
                            (Jsonb(list(gone_tokens)), country_code))

            # Only add those names that are not yet in the list.
            new_tokens = word_tokens - existing_tokens[True]
            if not internal:
                new_tokens -= existing_tokens[False]
            if new_tokens:
                if internal:
                    sql = """INSERT INTO word (word_token, type, word, info)
                               (SELECT data->>0, 'C', data->>1,
                                       jsonb_build_object('internal', 'yes', 'cc', %s::text)
                                  FROM jsonb_array_elements(%s) as data)
                           """
                else:
                    sql = """INSERT INTO word (word_token, type, word, info)
                                   (SELECT data->>0, 'C', data->>1,
                                           jsonb_build_object('cc', %s::text)
                                    FROM  jsonb_array_elements(%s) as data)
                          """
                cur.execute(sql, (country_code, Jsonb(list(new_tokens))))

    def process_place(self, place: PlaceInfo) -> Mapping[str, Any]:
        """ Determine tokenizer information about the given place.

            Returns a JSON-serializable structure that will be handed into
            the database via the token_info field.
        """
        token_info = _TokenInfo()

        names, address = self.sanitizer.process_names(place)

        if names:
            token_info.set_names(*self._compute_name_tokens(names))

            if place.is_country():
                assert place.country_code is not None
                self._add_country_full_names(place.country_code, names)

        if address:
            self._process_place_address(token_info, address)

        return token_info.to_dict()

    def _process_place_address(self, token_info: '_TokenInfo',
                               address: Sequence[PlaceName]) -> None:
        for item in address:
            if item.kind == 'postcode':
                token_info.set_postcode(self._add_postcode(item))
            elif item.kind == 'housenumber':
                token_info.add_housenumber(*self._compute_housenumber_token(item))
            elif item.kind == 'street':
                token_info.add_street(self._retrieve_full_tokens(item.name))
            elif item.kind == 'place':
                if not item.suffix:
                    token_info.add_place(itertools.chain(*self._compute_name_tokens([item])))
            elif (not item.kind.startswith('_') and not item.suffix and
                  item.kind not in ('country', 'full', 'inclusion')):
                token_info.add_address_term(item.kind,
                                            itertools.chain(*self._compute_name_tokens([item])))

    def _compute_housenumber_token(self, hnr: PlaceName) -> Tuple[Optional[int], Optional[str]]:
        """ Normalize the housenumber and return the word token and the
            canonical form.
        """
        assert self.conn is not None
        analyzer = self.token_analysis.analysis.get('@housenumber')
        result: Tuple[Optional[int], Optional[str]] = (None, None)

        if analyzer is None:
            # When no custom analyzer is set, simply normalize and transliterate
            norm_name = self._search_normalized(hnr.name)
            if norm_name:
                result = self._cache.housenumbers.get(norm_name, result)
                if result[0] is None:
                    hid = execute_scalar(self.conn, "SELECT getorcreate_hnr_id(%s)", (norm_name, ))

                    result = hid, norm_name
                    self._cache.housenumbers[norm_name] = result
        else:
            # Otherwise use the analyzer to determine the canonical name.
            # Per convention we use the first variant as the 'lookup name', the
            # name that gets saved in the housenumber field of the place.
            word_id = analyzer.get_canonical_id(hnr)
            if word_id:
                result = self._cache.housenumbers.get(word_id, result)
                if result[0] is None:
                    varout = analyzer.compute_variants(word_id)
                    if isinstance(varout, tuple):
                        variants = varout[0]
                    else:
                        variants = varout
                    if variants:
                        hid = execute_scalar(self.conn, "SELECT create_analyzed_hnr_id(%s, %s)",
                                             (word_id, variants))
                        result = hid, variants[0]
                        self._cache.housenumbers[word_id] = result

        return result

    def _retrieve_full_tokens(self, name: str) -> List[int]:
        """ Get the full name token for the given name, if it exists.
            The name is only retrieved for the standard analyser.
        """
        assert self.conn is not None
        norm_name = self._search_normalized(name)

        # return cached if possible
        if norm_name in self._cache.fulls:
            return self._cache.fulls[norm_name]

        with self.conn.cursor() as cur:
            cur.execute("SELECT word_id FROM word WHERE word_token = %s and type = 'W'",
                        (norm_name, ))
            full = [row[0] for row in cur]

        self._cache.fulls[norm_name] = full

        return full

    def _compute_name_tokens(self, names: Sequence[PlaceName]) -> Tuple[Set[int], Set[int]]:
        """ Computes the full name and partial name tokens for the given
            dictionary of names.
        """
        assert self.conn is not None
        full_tokens: Set[int] = set()
        partial_tokens: Set[int] = set()

        for name in names:
            analyzer_id = name.get_attr('analyzer')
            analyzer = self.token_analysis.get_analyzer(analyzer_id)
            word_id = analyzer.get_canonical_id(name)
            if analyzer_id is None:
                token_id = word_id
            else:
                token_id = f'{word_id}@{analyzer_id}'

            full, part = self._cache.names.get(token_id, (None, None))
            if full is None:
                varset = analyzer.compute_variants(word_id)
                if isinstance(varset, tuple):
                    variants, lookups = varset
                else:
                    variants, lookups = varset, None
                if not variants:
                    continue

                with self.conn.cursor() as cur:
                    cur.execute("SELECT * FROM getorcreate_full_word(%s, %s, %s)",
                                (token_id, variants, lookups))
                    full, part = cast(Tuple[int, List[int]], cur.fetchone())

                self._cache.names[token_id] = (full, part)

            assert part is not None

            full_tokens.add(full)
            partial_tokens.update(part)

        return full_tokens, partial_tokens

    def _add_postcode(self, item: PlaceName) -> Optional[str]:
        """ Make sure the normalized postcode is present in the word table.
        """
        assert self.conn is not None
        analyzer = self.token_analysis.analysis.get('@postcode')

        if analyzer is None:
            return item.name.strip().upper()
        else:
            return analyzer.get_canonical_id(item)


class _TokenInfo:
    """ Collect token information to be sent back to the database.
    """
    def __init__(self) -> None:
        self.names: Optional[str] = None
        self.housenumbers: Set[str] = set()
        self.housenumber_tokens: Set[int] = set()
        self.street_tokens: Optional[Set[int]] = None
        self.place_tokens: Set[int] = set()
        self.address_tokens: Dict[str, str] = {}
        self.postcode: Optional[str] = None

    def _mk_array(self, tokens: Iterable[Any]) -> str:
        return f"{{{','.join((str(s) for s in tokens))}}}"

    def to_dict(self) -> Dict[str, Any]:
        """ Return the token information in database importable format.
        """
        out: Dict[str, Any] = {}

        if self.names:
            out['names'] = self.names

        if self.housenumbers:
            out['hnr'] = ';'.join(self.housenumbers)
            out['hnr_tokens'] = self._mk_array(self.housenumber_tokens)

        if self.street_tokens is not None:
            out['street'] = self._mk_array(self.street_tokens)

        if self.place_tokens:
            out['place'] = self._mk_array(self.place_tokens)

        if self.address_tokens:
            out['addr'] = self.address_tokens

        if self.postcode:
            out['postcode'] = self.postcode

        return out

    def set_names(self, fulls: Iterable[int], partials: Iterable[int]) -> None:
        """ Adds token information for the normalised names.
        """
        self.names = self._mk_array(itertools.chain(fulls, partials))

    def add_housenumber(self, token: Optional[int], hnr: Optional[str]) -> None:
        """ Extract housenumber information from a list of normalised
            housenumbers.
        """
        if token:
            assert hnr is not None
            self.housenumbers.add(hnr)
            self.housenumber_tokens.add(token)

    def add_street(self, tokens: Iterable[int]) -> None:
        """ Add addr:street match terms.
        """
        if self.street_tokens is None:
            self.street_tokens = set()
        self.street_tokens.update(tokens)

    def add_place(self, tokens: Iterable[int]) -> None:
        """ Add addr:place search and match terms.
        """
        self.place_tokens.update(tokens)

    def add_address_term(self, key: str, partials: Iterable[int]) -> None:
        """ Add additional address terms.
        """
        array = self._mk_array(partials)
        if len(array) > 2:
            self.address_tokens[key] = array

    def set_postcode(self, postcode: Optional[str]) -> None:
        """ Set the postcode to the given one.
        """
        self.postcode = postcode


class _TokenCache:
    """ Cache for token information to avoid repeated database queries.

        This cache is not thread-safe and needs to be instantiated per
        analyzer.
    """
    def __init__(self) -> None:
        self.names: Dict[str, Tuple[int, List[int]]] = {}
        self.partials: Dict[str, int] = {}
        self.fulls: Dict[str, List[int]] = {}
        self.housenumbers: Dict[str, Tuple[Optional[int], Optional[str]]] = {}
