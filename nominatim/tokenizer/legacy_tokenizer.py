# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tokenizer implementing normalisation as used before Nominatim 4.
"""
from typing import Optional, Sequence, List, Tuple, Mapping, Any, Callable, \
                   cast, Dict, Set, Iterable
from collections import OrderedDict
import logging
from pathlib import Path
import re
import shutil
from textwrap import dedent

from icu import Transliterator
import psycopg2
import psycopg2.extras

from nominatim.db.connection import connect, Connection
from nominatim.config import Configuration
from nominatim.db import properties
from nominatim.db import utils as db_utils
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.data.place_info import PlaceInfo
from nominatim.errors import UsageError
from nominatim.tokenizer.base import AbstractAnalyzer, AbstractTokenizer

DBCFG_NORMALIZATION = "tokenizer_normalization"
DBCFG_MAXWORDFREQ = "tokenizer_maxwordfreq"

LOG = logging.getLogger()

def create(dsn: str, data_dir: Path) -> 'LegacyTokenizer':
    """ Create a new instance of the tokenizer provided by this module.
    """
    return LegacyTokenizer(dsn, data_dir)


def _install_module(config_module_path: str, src_dir: Path, module_dir: Path) -> str:
    """ Copies the PostgreSQL normalisation module into the project
        directory if necessary. For historical reasons the module is
        saved in the '/module' subdirectory and not with the other tokenizer
        data.

        The function detects when the installation is run from the
        build directory. It doesn't touch the module in that case.
    """
    # Custom module locations are simply used as is.
    if config_module_path:
        LOG.info("Using custom path for database module at '%s'", config_module_path)
        return config_module_path

    # Compatibility mode for builddir installations.
    if module_dir.exists() and src_dir.samefile(module_dir):
        LOG.info('Running from build directory. Leaving database module as is.')
        return str(module_dir)

    # In any other case install the module in the project directory.
    if not module_dir.exists():
        module_dir.mkdir()

    destfile = module_dir / 'nominatim.so'
    shutil.copy(str(src_dir / 'nominatim.so'), str(destfile))
    destfile.chmod(0o755)

    LOG.info('Database module installed at %s', str(destfile))

    return str(module_dir)


def _check_module(module_dir: str, conn: Connection) -> None:
    """ Try to use the PostgreSQL module to confirm that it is correctly
        installed and accessible from PostgreSQL.
    """
    with conn.cursor() as cur:
        try:
            cur.execute("""CREATE FUNCTION nominatim_test_import_func(text)
                           RETURNS text AS %s, 'transliteration'
                           LANGUAGE c IMMUTABLE STRICT;
                           DROP FUNCTION nominatim_test_import_func(text)
                        """, (f'{module_dir}/nominatim.so', ))
        except psycopg2.DatabaseError as err:
            LOG.fatal("Error accessing database module: %s", err)
            raise UsageError("Database module cannot be accessed.") from err


class LegacyTokenizer(AbstractTokenizer):
    """ The legacy tokenizer uses a special PostgreSQL module to normalize
        names and queries. The tokenizer thus implements normalization through
        calls to the database.
    """

    def __init__(self, dsn: str, data_dir: Path) -> None:
        self.dsn = dsn
        self.data_dir = data_dir
        self.normalization: Optional[str] = None


    def init_new_db(self, config: Configuration, init_db: bool = True) -> None:
        """ Set up a new tokenizer for the database.

            This copies all necessary data in the project directory to make
            sure the tokenizer remains stable even over updates.
        """
        assert config.project_dir is not None
        module_dir = _install_module(config.DATABASE_MODULE_PATH,
                                     config.lib_dir.module,
                                     config.project_dir / 'module')

        self.normalization = config.TERM_NORMALIZATION

        self._install_php(config, overwrite=True)

        with connect(self.dsn) as conn:
            _check_module(module_dir, conn)
            self._save_config(conn, config)
            conn.commit()

        if init_db:
            self.update_sql_functions(config)
            self._init_db_tables(config)


    def init_from_project(self, config: Configuration) -> None:
        """ Initialise the tokenizer from the project directory.
        """
        assert config.project_dir is not None

        with connect(self.dsn) as conn:
            self.normalization = properties.get_property(conn, DBCFG_NORMALIZATION)

        if not (config.project_dir / 'module' / 'nominatim.so').exists():
            _install_module(config.DATABASE_MODULE_PATH,
                            config.lib_dir.module,
                            config.project_dir / 'module')

        self._install_php(config, overwrite=False)

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
        assert config.project_dir is not None

        with connect(self.dsn) as conn:
            max_word_freq = properties.get_property(conn, DBCFG_MAXWORDFREQ)
            modulepath = config.DATABASE_MODULE_PATH or \
                         str((config.project_dir / 'module').resolve())
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_tokenizer.sql',
                              max_word_freq=max_word_freq,
                              modulepath=modulepath)


    def check_database(self, _: Configuration) -> Optional[str]:
        """ Check that the tokenizer is set up correctly.
        """
        hint = """\
             The Postgresql extension nominatim.so was not correctly loaded.

             Error: {error}

             Hints:
             * Check the output of the CMmake/make installation step
             * Does nominatim.so exist?
             * Does nominatim.so exist on the database server?
             * Can nominatim.so be accessed by the database user?
             """
        with connect(self.dsn) as conn:
            with conn.cursor() as cur:
                try:
                    out = cur.scalar("SELECT make_standard_name('a')")
                except psycopg2.Error as err:
                    return hint.format(error=str(err))

        if out != 'a':
            return hint.format(error='Unexpected result for make_standard_name()')

        return None


    def migrate_database(self, config: Configuration) -> None:
        """ Initialise the project directory of an existing database for
            use with this tokenizer.

            This is a special migration function for updating existing databases
            to new software versions.
        """
        assert config.project_dir is not None

        self.normalization = config.TERM_NORMALIZATION
        module_dir = _install_module(config.DATABASE_MODULE_PATH,
                                     config.lib_dir.module,
                                     config.project_dir / 'module')

        with connect(self.dsn) as conn:
            _check_module(module_dir, conn)
            self._save_config(conn, config)


    def update_statistics(self) -> None:
        """ Recompute the frequency of full words.
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
                    cur.execute("""UPDATE word SET search_name_count = count
                                   FROM word_frequencies
                                   WHERE word_token like ' %' and word_id = id""")
                    cur.drop_table("word_frequencies")
            conn.commit()


    def update_word_tokens(self) -> None:
        """ No house-keeping implemented for the legacy tokenizer.
        """
        LOG.info("No tokenizer clean-up available.")


    def name_analyzer(self) -> 'LegacyNameAnalyzer':
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
        normalizer = Transliterator.createFromRules("phrase normalizer",
                                                    self.normalization)
        return LegacyNameAnalyzer(self.dsn, normalizer)


    def _install_php(self, config: Configuration, overwrite: bool = True) -> None:
        """ Install the php script for the tokenizer.
        """
        php_file = self.data_dir / "tokenizer.php"

        if not php_file.exists() or overwrite:
            php_file.write_text(dedent(f"""\
                <?php
                @define('CONST_Max_Word_Frequency', {config.MAX_WORD_FREQUENCY});
                @define('CONST_Term_Normalization_Rules', "{config.TERM_NORMALIZATION}");
                require_once('{config.lib_dir.php}/tokenizer/legacy_tokenizer.php');
                """), encoding='utf-8')


    def _init_db_tables(self, config: Configuration) -> None:
        """ Set up the word table and fill it with pre-computed word
            frequencies.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_tokenizer_tables.sql')
            conn.commit()

        LOG.warning("Precomputing word tokens")
        db_utils.execute_file(self.dsn, config.lib_dir.data / 'words.sql')


    def _save_config(self, conn: Connection, config: Configuration) -> None:
        """ Save the configuration that needs to remain stable for the given
            database as database properties.
        """
        assert self.normalization is not None

        properties.set_property(conn, DBCFG_NORMALIZATION, self.normalization)
        properties.set_property(conn, DBCFG_MAXWORDFREQ, config.MAX_WORD_FREQUENCY)


class LegacyNameAnalyzer(AbstractAnalyzer):
    """ The legacy analyzer uses the special Postgresql module for
        splitting names.

        Each instance opens a connection to the database to request the
        normalization.
    """

    def __init__(self, dsn: str, normalizer: Any):
        self.conn: Optional[Connection] = connect(dsn).connection
        self.conn.autocommit = True
        self.normalizer = normalizer
        psycopg2.extras.register_hstore(self.conn)

        self._cache = _TokenCache(self.conn)


    def close(self) -> None:
        """ Free all resources used by the analyzer.
        """
        if self.conn:
            self.conn.close()
            self.conn = None


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
        with self.conn.cursor() as cur:
            cur.execute("""SELECT t.term, word_token, word_id
                           FROM word, (SELECT unnest(%s::TEXT[]) as term) t
                           WHERE word_token = (CASE
                                   WHEN left(t.term, 1) = '#' THEN
                                     ' ' || make_standard_name(substring(t.term from 2))
                                   ELSE
                                     make_standard_name(t.term)
                                   END)
                                 and class is null and country_code is null""",
                        (words, ))

            return [(r[0], r[1], r[2]) for r in cur]


    def normalize(self, phrase: str) -> str:
        """ Normalize the given phrase, i.e. remove all properties that
            are irrelevant for search.
        """
        return cast(str, self.normalizer.transliterate(phrase))


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

        with self.conn.cursor() as cur:
            # This finds us the rows in location_postcode and word that are
            # missing in the other table.
            cur.execute("""SELECT * FROM
                            (SELECT pc, word FROM
                              (SELECT distinct(postcode) as pc FROM location_postcode) p
                              FULL JOIN
                              (SELECT word FROM word
                                WHERE class ='place' and type = 'postcode') w
                              ON pc = word) x
                           WHERE pc is null or word is null""")

            to_delete = []
            to_add = []

            for postcode, word in cur:
                if postcode is None:
                    to_delete.append(word)
                else:
                    to_add.append(postcode)

            if to_delete:
                cur.execute("""DELETE FROM WORD
                               WHERE class ='place' and type = 'postcode'
                                     and word = any(%s)
                            """, (to_delete, ))
            if to_add:
                cur.execute("""SELECT count(create_postcode_id(pc))
                               FROM unnest(%s) as pc
                            """, (to_add, ))



    def update_special_phrases(self, phrases: Iterable[Tuple[str, str, str, str]],
                               should_replace: bool) -> None:
        """ Replace the search index for special phrases with the new phrases.
        """
        assert self.conn is not None

        norm_phrases = set(((self.normalize(p[0]), p[1], p[2], p[3])
                            for p in phrases))

        with self.conn.cursor() as cur:
            # Get the old phrases.
            existing_phrases = set()
            cur.execute("""SELECT word, class, type, operator FROM word
                           WHERE class != 'place'
                                 OR (type != 'house' AND type != 'postcode')""")
            for label, cls, typ, oper in cur:
                existing_phrases.add((label, cls, typ, oper or '-'))

            to_add = norm_phrases - existing_phrases
            to_delete = existing_phrases - norm_phrases

            if to_add:
                cur.execute_values(
                    """ INSERT INTO word (word_id, word_token, word, class, type,
                                          search_name_count, operator)
                        (SELECT nextval('seq_word'), ' ' || make_standard_name(name), name,
                                class, type, 0,
                                CASE WHEN op in ('in', 'near') THEN op ELSE null END
                           FROM (VALUES %s) as v(name, class, type, op))""",
                    to_add)

            if to_delete and should_replace:
                cur.execute_values(
                    """ DELETE FROM word USING (VALUES %s) as v(name, in_class, in_type, op)
                        WHERE word = name and class = in_class and type = in_type
                              and ((op = '-' and operator is null) or op = operator)""",
                    to_delete)

        LOG.info("Total phrases: %s. Added: %s. Deleted: %s",
                 len(norm_phrases), len(to_add), len(to_delete))


    def add_country_names(self, country_code: str, names: Mapping[str, str]) -> None:
        """ Add names for the given country to the search index.
        """
        assert self.conn is not None

        with self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO word (word_id, word_token, country_code)
                   (SELECT nextval('seq_word'), lookup_token, %s
                      FROM (SELECT DISTINCT ' ' || make_standard_name(n) as lookup_token
                            FROM unnest(%s)n) y
                      WHERE NOT EXISTS(SELECT * FROM word
                                       WHERE word_token = lookup_token and country_code = %s))
                """, (country_code, list(names.values()), country_code))


    def process_place(self, place: PlaceInfo) -> Mapping[str, Any]:
        """ Determine tokenizer information about the given place.

            Returns a JSON-serialisable structure that will be handed into
            the database via the token_info field.
        """
        assert self.conn is not None

        token_info = _TokenInfo(self._cache)

        names = place.name

        if names:
            token_info.add_names(self.conn, names)

            if place.is_country():
                assert place.country_code is not None
                self.add_country_names(place.country_code, names)

        address = place.address
        if address:
            self._process_place_address(token_info, address)

        return token_info.data


    def _process_place_address(self, token_info: '_TokenInfo', address: Mapping[str, str]) -> None:
        assert self.conn is not None
        hnrs = []
        addr_terms = []

        for key, value in address.items():
            if key == 'postcode':
                # Make sure the normalized postcode is present in the word table.
                if re.search(r'[:,;]', value) is None:
                    norm_pc = self.normalize_postcode(value)
                    token_info.set_postcode(norm_pc)
                    self._cache.add_postcode(self.conn, norm_pc)
            elif key in ('housenumber', 'streetnumber', 'conscriptionnumber'):
                hnrs.append(value)
            elif key == 'street':
                token_info.add_street(self.conn, value)
            elif key == 'place':
                token_info.add_place(self.conn, value)
            elif not key.startswith('_') \
                 and key not in ('country', 'full', 'inclusion'):
                addr_terms.append((key, value))

        if hnrs:
            token_info.add_housenumbers(self.conn, hnrs)

        if addr_terms:
            token_info.add_address_terms(self.conn, addr_terms)



class _TokenInfo:
    """ Collect token information to be sent back to the database.
    """
    def __init__(self, cache: '_TokenCache') -> None:
        self.cache = cache
        self.data: Dict[str, Any] = {}


    def add_names(self, conn: Connection, names: Mapping[str, str]) -> None:
        """ Add token information for the names of the place.
        """
        with conn.cursor() as cur:
            # Create the token IDs for all names.
            self.data['names'] = cur.scalar("SELECT make_keywords(%s)::text",
                                            (names, ))


    def add_housenumbers(self, conn: Connection, hnrs: Sequence[str]) -> None:
        """ Extract housenumber information from the address.
        """
        if len(hnrs) == 1:
            token = self.cache.get_housenumber(hnrs[0])
            if token is not None:
                self.data['hnr_tokens'] = token
                self.data['hnr'] = hnrs[0]
                return

        # split numbers if necessary
        simple_list: List[str] = []
        for hnr in hnrs:
            simple_list.extend((x.strip() for x in re.split(r'[;,]', hnr)))

        if len(simple_list) > 1:
            simple_list = list(set(simple_list))

        with conn.cursor() as cur:
            cur.execute("SELECT * FROM create_housenumbers(%s)", (simple_list, ))
            result = cur.fetchone()
            assert result is not None
            self.data['hnr_tokens'], self.data['hnr'] = result


    def set_postcode(self, postcode: str) -> None:
        """ Set or replace the postcode token with the given value.
        """
        self.data['postcode'] = postcode

    def add_street(self, conn: Connection, street: str) -> None:
        """ Add addr:street match terms.
        """
        def _get_street(name: str) -> List[int]:
            with conn.cursor() as cur:
                return cast(List[int],
                            cur.scalar("SELECT word_ids_from_name(%s)::text", (name, )))

        tokens = self.cache.streets.get(street, _get_street)
        if tokens:
            self.data['street'] = tokens


    def add_place(self, conn: Connection, place: str) -> None:
        """ Add addr:place search and match terms.
        """
        def _get_place(name: str) -> Tuple[List[int], List[int]]:
            with conn.cursor() as cur:
                cur.execute("""SELECT make_keywords(hstore('name' , %s))::text,
                                      word_ids_from_name(%s)::text""",
                            (name, name))
                return cast(Tuple[List[int], List[int]], cur.fetchone())

        self.data['place_search'], self.data['place_match'] = \
            self.cache.places.get(place, _get_place)


    def add_address_terms(self, conn: Connection, terms: Sequence[Tuple[str, str]]) -> None:
        """ Add additional address terms.
        """
        def _get_address_term(name: str) -> Tuple[List[int], List[int]]:
            with conn.cursor() as cur:
                cur.execute("""SELECT addr_ids_from_name(%s)::text,
                                      word_ids_from_name(%s)::text""",
                            (name, name))
                return cast(Tuple[List[int], List[int]], cur.fetchone())

        tokens = {}
        for key, value in terms:
            items = self.cache.address_terms.get(value, _get_address_term)
            if items[0] or items[1]:
                tokens[key] = items

        if tokens:
            self.data['addr'] = tokens


class _LRU:
    """ Least recently used cache that accepts a generator function to
        produce the item when there is a cache miss.
    """

    def __init__(self, maxsize: int = 128):
        self.data: 'OrderedDict[str, Any]' = OrderedDict()
        self.maxsize = maxsize


    def get(self, key: str, generator: Callable[[str], Any]) -> Any:
        """ Get the item with the given key from the cache. If nothing
            is found in the cache, generate the value through the
            generator function and store it in the cache.
        """
        value = self.data.get(key)
        if value is not None:
            self.data.move_to_end(key)
        else:
            value = generator(key)
            if len(self.data) >= self.maxsize:
                self.data.popitem(last=False)
            self.data[key] = value

        return value


class _TokenCache:
    """ Cache for token information to avoid repeated database queries.

        This cache is not thread-safe and needs to be instantiated per
        analyzer.
    """
    def __init__(self, conn: Connection):
        # various LRU caches
        self.streets = _LRU(maxsize=256)
        self.places = _LRU(maxsize=128)
        self.address_terms = _LRU(maxsize=1024)

        # Lookup houseunumbers up to 100 and cache them
        with conn.cursor() as cur:
            cur.execute("""SELECT i, ARRAY[getorcreate_housenumber_id(i::text)]::text
                           FROM generate_series(1, 100) as i""")
            self._cached_housenumbers: Dict[str, str] = {str(r[0]): r[1] for r in cur}

        # For postcodes remember the ones that have already been added
        self.postcodes: Set[str] = set()

    def get_housenumber(self, number: str) -> Optional[str]:
        """ Get a housenumber token from the cache.
        """
        return self._cached_housenumbers.get(number)


    def add_postcode(self, conn: Connection, postcode: str) -> None:
        """ Make sure the given postcode is in the database.
        """
        if postcode not in self.postcodes:
            with conn.cursor() as cur:
                cur.execute('SELECT create_postcode_id(%s)', (postcode, ))
            self.postcodes.add(postcode)
