# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tokenizer implementing normalisation as used before Nominatim 4 but using
libICU instead of the PostgreSQL module.
"""
from typing import Optional, Sequence, List, Tuple, Mapping, Any, cast, \
                   Dict, Set, Iterable
import itertools
import json
import logging
from pathlib import Path
from textwrap import dedent

from nominatim.db.connection import connect, Connection, Cursor
from nominatim.config import Configuration
from nominatim.db.utils import CopyBuffer
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.data.place_info import PlaceInfo
from nominatim.tokenizer.icu_rule_loader import ICURuleLoader
from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.data.place_name import PlaceName
from nominatim.tokenizer.icu_token_analysis import ICUTokenAnalysis
from nominatim.tokenizer.base import AbstractAnalyzer, AbstractTokenizer

DBCFG_TERM_NORMALIZATION = "tokenizer_term_normalization"

LOG = logging.getLogger()

def create(dsn: str, data_dir: Path) -> 'ICUTokenizer':
    """ Create a new instance of the tokenizer provided by this module.
    """
    return ICUTokenizer(dsn, data_dir)


class ICUTokenizer(AbstractTokenizer):
    """ This tokenizer uses libICU to convert names and queries to ASCII.
        Otherwise it uses the same algorithms and data structures as the
        normalization routines in Nominatim 3.
    """

    def __init__(self, dsn: str, data_dir: Path) -> None:
        self.dsn = dsn
        self.data_dir = data_dir
        self.loader: Optional[ICURuleLoader] = None


    def init_new_db(self, config: Configuration, init_db: bool = True) -> None:
        """ Set up a new tokenizer for the database.

            This copies all necessary data in the project directory to make
            sure the tokenizer remains stable even over updates.
        """
        self.loader = ICURuleLoader(config)

        self._install_php(config.lib_dir.php, overwrite=True)
        self._save_config()

        if init_db:
            self.update_sql_functions(config)
            self._init_db_tables(config)


    def init_from_project(self, config: Configuration) -> None:
        """ Initialise the tokenizer from the project directory.
        """
        self.loader = ICURuleLoader(config)

        with connect(self.dsn) as conn:
            self.loader.load_config_from_db(conn)

        self._install_php(config.lib_dir.php, overwrite=False)


    def finalize_import(self, config: Configuration) -> None:
        """ Do any required postprocessing to make the tokenizer data ready
            for use.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_tokenizer_indices.sql')


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


    def update_statistics(self) -> None:
        """ Recompute frequencies for all name words.
        """
        with connect(self.dsn) as conn:
            if conn.table_exists('search_name'):
                with conn.cursor() as cur:
                    cur.drop_table("word_frequencies")
                    LOG.info("Computing word frequencies")
                    cur.execute("""CREATE TEMP TABLE word_frequencies AS
                                     SELECT unnest(name_vector) as id, count(*)
                                     FROM search_name GROUP BY id""")
                    cur.execute("CREATE INDEX ON word_frequencies(id)")
                    LOG.info("Update word table with recomputed frequencies")
                    cur.execute("""UPDATE word
                                   SET info = info || jsonb_build_object('count', count)
                                   FROM word_frequencies WHERE word_id = id""")
                    cur.drop_table("word_frequencies")
            conn.commit()


    def _cleanup_housenumbers(self) -> None:
        """ Remove unused house numbers.
        """
        with connect(self.dsn) as conn:
            if not conn.table_exists('search_name'):
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


    def _install_php(self, phpdir: Path, overwrite: bool = True) -> None:
        """ Install the php script for the tokenizer.
        """
        assert self.loader is not None
        php_file = self.data_dir / "tokenizer.php"

        if not php_file.exists() or overwrite:
            php_file.write_text(dedent(f"""\
                <?php
                @define('CONST_Max_Word_Frequency', 10000000);
                @define('CONST_Term_Normalization_Rules', "{self.loader.normalization_rules}");
                @define('CONST_Transliteration', "{self.loader.get_search_rules()}");
                require_once('{phpdir}/tokenizer/icu_tokenizer.php');"""), encoding='utf-8')


    def _save_config(self) -> None:
        """ Save the configuration that needs to remain stable for the given
            database as database properties.
        """
        assert self.loader is not None
        with connect(self.dsn) as conn:
            self.loader.save_config_to_db(conn)


    def _init_db_tables(self, config: Configuration) -> None:
        """ Set up the word table and fill it with pre-computed word
            frequencies.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/icu_tokenizer_tables.sql')
            conn.commit()


class ICUNameAnalyzer(AbstractAnalyzer):
    """ The ICU analyzer uses the ICU library for splitting names.

        Each instance opens a connection to the database to request the
        normalization.
    """

    def __init__(self, dsn: str, sanitizer: PlaceSanitizer,
                 token_analysis: ICUTokenAnalysis) -> None:
        self.conn: Optional[Connection] = connect(dsn).connection
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


    def get_word_token_info(self, words: Sequence[str]) -> List[Tuple[str, str, int]]:
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
            full_ids = {r[0]: r[1] for r in cur}
            cur.execute("""SELECT word_token, word_id
                            FROM word WHERE word_token = ANY(%s) and type = 'w'""",
                        (list(partial_tokens.values()),))
            part_ids = {r[0]: r[1] for r in cur}

        return [(k, v, full_ids.get(v, None)) for k, v in full_tokens.items()] \
               + [(k, v, part_ids.get(v, None)) for k, v in partial_tokens.items()]


    def normalize_postcode(self, postcode: str) -> str:
        """ Convert the postcode to a standardized form.

            This function must yield exactly the same result as the SQL function
            'token_normalized_postcode()'.
        """
        return postcode.strip().upper()


    def update_postcodes_from_db(self) -> None:
        """ Update postcode tokens in the word table from the location_postcode
            table.
        """
        assert self.conn is not None
        analyzer = self.token_analysis.analysis.get('@postcode')

        with self.conn.cursor() as cur:
            # First get all postcode names currently in the word table.
            cur.execute("SELECT DISTINCT word FROM word WHERE type = 'P'")
            word_entries = set((entry[0] for entry in cur))

            # Then compute the required postcode names from the postcode table.
            needed_entries = set()
            cur.execute("SELECT country_code, postcode FROM location_postcode")
            for cc, postcode in cur:
                info = PlaceInfo({'country_code': cc,
                                  'class': 'place', 'type': 'postcode',
                                  'address': {'postcode': postcode}})
                address = self.sanitizer.process_names(info)[1]
                for place in address:
                    if place.kind == 'postcode':
                        if analyzer is None:
                            postcode_name = place.name.strip().upper()
                            variant_base = None
                        else:
                            postcode_name = analyzer.get_canonical_id(place)
                            variant_base = place.get_attr("variant")

                        if variant_base:
                            needed_entries.add(f'{postcode_name}@{variant_base}')
                        else:
                            needed_entries.add(postcode_name)
                        break

        # Now update the word table.
        self._delete_unused_postcode_words(word_entries - needed_entries)
        self._add_missing_postcode_words(needed_entries - word_entries)

    def _delete_unused_postcode_words(self, tokens: Iterable[str]) -> None:
        assert self.conn is not None
        if tokens:
            with self.conn.cursor() as cur:
                cur.execute("DELETE FROM word WHERE type = 'P' and word = any(%s)",
                            (list(tokens), ))

    def _add_missing_postcode_words(self, tokens: Iterable[str]) -> None:
        assert self.conn is not None
        if not tokens:
            return

        analyzer = self.token_analysis.analysis.get('@postcode')
        terms = []

        for postcode_name in tokens:
            if '@' in postcode_name:
                term, variant = postcode_name.split('@', 2)
                term = self._search_normalized(term)
                if analyzer is None:
                    variants = [term]
                else:
                    variants = analyzer.compute_variants(variant)
                    if term not in variants:
                        variants.append(term)
            else:
                variants = [self._search_normalized(postcode_name)]
            terms.append((postcode_name, variants))

        if terms:
            with self.conn.cursor() as cur:
                cur.execute_values("""SELECT create_postcode_word(pc, var)
                                      FROM (VALUES %s) AS v(pc, var)""",
                                   terms)




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
        with CopyBuffer() as copystr:
            for word, cls, typ, oper in to_add:
                term = self._search_normalized(word)
                if term:
                    copystr.add(term, 'S', word,
                                json.dumps({'class': cls, 'type': typ,
                                            'op': oper if oper in ('in', 'near') else None}))
                    added += 1

            copystr.copy_out(cursor, 'word',
                             columns=['word_token', 'type', 'word', 'info'])

        return added


    def _remove_special_phrases(self, cursor: Cursor,
                             new_phrases: Set[Tuple[str, str, str, str]],
                             existing_phrases: Set[Tuple[str, str, str, str]]) -> int:
        """ Remove all phrases from the database that are no longer in the
            new phrase list.
        """
        to_delete = existing_phrases - new_phrases

        if to_delete:
            cursor.execute_values(
                """ DELETE FROM word USING (VALUES %s) as v(name, in_class, in_type, op)
                    WHERE type = 'S' and word = name
                          and info->>'class' = in_class and info->>'type' = in_type
                          and ((op = '-' and info->>'op' is null) or op = info->>'op')
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
            norm_name = self._search_normalized(name.name)
            if norm_name:
                word_tokens.add(norm_name)

        with self.conn.cursor() as cur:
            # Get existing names
            cur.execute("""SELECT word_token, coalesce(info ? 'internal', false) as is_internal
                             FROM word
                             WHERE type = 'C' and word = %s""",
                        (country_code, ))
            # internal/external names
            existing_tokens: Dict[bool, Set[str]] = {True: set(), False: set()}
            for word in cur:
                existing_tokens[word[1]].add(word[0])

            # Delete names that no longer exist.
            gone_tokens = existing_tokens[internal] - word_tokens
            if internal:
                gone_tokens.update(existing_tokens[False] & word_tokens)
            if gone_tokens:
                cur.execute("""DELETE FROM word
                               USING unnest(%s) as token
                               WHERE type = 'C' and word = %s
                                     and word_token = token""",
                            (list(gone_tokens), country_code))

            # Only add those names that are not yet in the list.
            new_tokens = word_tokens - existing_tokens[True]
            if not internal:
                new_tokens -= existing_tokens[False]
            if new_tokens:
                if internal:
                    sql = """INSERT INTO word (word_token, type, word, info)
                               (SELECT token, 'C', %s, '{"internal": "yes"}'
                                  FROM unnest(%s) as token)
                           """
                else:
                    sql = """INSERT INTO word (word_token, type, word)
                                   (SELECT token, 'C', %s
                                    FROM unnest(%s) as token)
                          """
                cur.execute(sql, (country_code, list(new_tokens)))


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
                    token_info.add_place(self._compute_partial_tokens(item.name))
            elif not item.kind.startswith('_') and not item.suffix and \
                 item.kind not in ('country', 'full', 'inclusion'):
                token_info.add_address_term(item.kind, self._compute_partial_tokens(item.name))


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
                    with self.conn.cursor() as cur:
                        hid = cur.scalar("SELECT getorcreate_hnr_id(%s)", (norm_name, ))

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
                    variants = analyzer.compute_variants(word_id)
                    if variants:
                        with self.conn.cursor() as cur:
                            hid = cur.scalar("SELECT create_analyzed_hnr_id(%s, %s)",
                                             (word_id, list(variants)))
                            result = hid, variants[0]
                            self._cache.housenumbers[word_id] = result

        return result


    def _compute_partial_tokens(self, name: str) -> List[int]:
        """ Normalize the given term, split it into partial words and return
            then token list for them.
        """
        assert self.conn is not None
        norm_name = self._search_normalized(name)

        tokens = []
        need_lookup = []
        for partial in norm_name.split():
            token = self._cache.partials.get(partial)
            if token:
                tokens.append(token)
            else:
                need_lookup.append(partial)

        if need_lookup:
            with self.conn.cursor() as cur:
                cur.execute("""SELECT word, getorcreate_partial_word(word)
                               FROM unnest(%s) word""",
                            (need_lookup, ))

                for partial, token in cur:
                    assert token is not None
                    tokens.append(token)
                    self._cache.partials[partial] = token

        return tokens


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
                variants = analyzer.compute_variants(word_id)
                if not variants:
                    continue

                with self.conn.cursor() as cur:
                    cur.execute("SELECT * FROM getorcreate_full_word(%s, %s)",
                                (token_id, variants))
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
            postcode_name = item.name.strip().upper()
            variant_base = None
        else:
            postcode_name = analyzer.get_canonical_id(item)
            variant_base = item.get_attr("variant")

        if variant_base:
            postcode = f'{postcode_name}@{variant_base}'
        else:
            postcode = postcode_name

        if postcode not in self._cache.postcodes:
            term = self._search_normalized(postcode_name)
            if not term:
                return None

            variants = {term}
            if analyzer is not None and variant_base:
                variants.update(analyzer.compute_variants(variant_base))

            with self.conn.cursor() as cur:
                cur.execute("SELECT create_postcode_word(%s, %s)",
                            (postcode, list(variants)))
            self._cache.postcodes.add(postcode)

        return postcode_name


class _TokenInfo:
    """ Collect token information to be sent back to the database.
    """
    def __init__(self) -> None:
        self.names: Optional[str] = None
        self.housenumbers: Set[str] = set()
        self.housenumber_tokens: Set[int] = set()
        self.street_tokens: Set[int] = set()
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

        if self.street_tokens:
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
        self.street_tokens.update(tokens)


    def add_place(self, tokens: Iterable[int]) -> None:
        """ Add addr:place search and match terms.
        """
        self.place_tokens.update(tokens)


    def add_address_term(self, key: str, partials: Iterable[int]) -> None:
        """ Add additional address terms.
        """
        if partials:
            self.address_tokens[key] = self._mk_array(partials)

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
        self.postcodes: Set[str] = set()
        self.housenumbers: Dict[str, Tuple[Optional[int], Optional[str]]] = {}
