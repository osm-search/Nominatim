"""
Tokenizer implementing normalisation as used before Nominatim 4 but using
libICU instead of the PostgreSQL module.
"""
from collections import Counter
import functools
import io
import itertools
import json
import logging
import re
from textwrap import dedent
from pathlib import Path

from icu import Transliterator
import psycopg2.extras

from nominatim.db.connection import connect
from nominatim.db.properties import set_property, get_property
from nominatim.db.sql_preprocessor import SQLPreprocessor

DBCFG_NORMALIZATION = "tokenizer_normalization"
DBCFG_MAXWORDFREQ = "tokenizer_maxwordfreq"
DBCFG_TRANSLITERATION = "tokenizer_transliteration"
DBCFG_ABBREVIATIONS = "tokenizer_abbreviations"

LOG = logging.getLogger()

def create(dsn, data_dir):
    """ Create a new instance of the tokenizer provided by this module.
    """
    return LegacyICUTokenizer(dsn, data_dir)


class LegacyICUTokenizer:
    """ This tokenizer uses libICU to covert names and queries to ASCII.
        Otherwise it uses the same algorithms and data structures as the
        normalization routines in Nominatim 3.
    """

    def __init__(self, dsn, data_dir):
        self.dsn = dsn
        self.data_dir = data_dir
        self.normalization = None
        self.transliteration = None
        self.abbreviations = None


    def init_new_db(self, config, init_db=True):
        """ Set up a new tokenizer for the database.

            This copies all necessary data in the project directory to make
            sure the tokenizer remains stable even over updates.
        """
        if config.TOKENIZER_CONFIG:
            cfgfile = Path(config.TOKENIZER_CONFIG)
        else:
            cfgfile = config.config_dir / 'legacy_icu_tokenizer.json'

        rules = json.loads(cfgfile.read_text())
        self.transliteration = ';'.join(rules['normalization']) + ';'
        self.abbreviations = rules["abbreviations"]
        self.normalization = config.TERM_NORMALIZATION

        self._install_php(config)
        self._save_config(config)

        if init_db:
            self.update_sql_functions(config)
            self._init_db_tables(config)


    def init_from_project(self):
        """ Initialise the tokenizer from the project directory.
        """
        with connect(self.dsn) as conn:
            self.normalization = get_property(conn, DBCFG_NORMALIZATION)
            self.transliteration = get_property(conn, DBCFG_TRANSLITERATION)
            self.abbreviations = json.loads(get_property(conn, DBCFG_ABBREVIATIONS))


    def finalize_import(self, config):
        """ Do any required postprocessing to make the tokenizer data ready
            for use.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_tokenizer_indices.sql')


    def update_sql_functions(self, config):
        """ Reimport the SQL functions for this tokenizer.
        """
        with connect(self.dsn) as conn:
            max_word_freq = get_property(conn, DBCFG_MAXWORDFREQ)
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_icu_tokenizer.sql',
                              max_word_freq=max_word_freq)


    def check_database(self):
        """ Check that the tokenizer is set up correctly.
        """
        self.init_from_project()

        if self.normalization is None\
           or self.transliteration is None\
           or self.abbreviations is None:
            return "Configuration for tokenizer 'legacy_icu' are missing."

        return None


    def name_analyzer(self):
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
        norm = Transliterator.createFromRules("normalizer", self.normalization)
        trans = Transliterator.createFromRules("trans", self.transliteration)
        return LegacyICUNameAnalyzer(self.dsn, norm, trans, self.abbreviations)


    def _install_php(self, config):
        """ Install the php script for the tokenizer.
        """
        abbr_inverse = list(zip(*self.abbreviations))
        php_file = self.data_dir / "tokenizer.php"
        php_file.write_text(dedent("""\
            <?php
            @define('CONST_Max_Word_Frequency', {1.MAX_WORD_FREQUENCY});
            @define('CONST_Term_Normalization_Rules', "{0.normalization}");
            @define('CONST_Transliteration', "{0.transliteration}");
            @define('CONST_Abbreviations', array(array('{2}'), array('{3}')));
            require_once('{1.lib_dir.php}/tokenizer/legacy_icu_tokenizer.php');
            """.format(self, config,
                       "','".join(abbr_inverse[0]),
                       "','".join(abbr_inverse[1]))))


    def _save_config(self, config):
        """ Save the configuration that needs to remain stable for the given
            database as database properties.
        """
        with connect(self.dsn) as conn:
            set_property(conn, DBCFG_NORMALIZATION, self.normalization)
            set_property(conn, DBCFG_MAXWORDFREQ, config.MAX_WORD_FREQUENCY)
            set_property(conn, DBCFG_TRANSLITERATION, self.transliteration)
            set_property(conn, DBCFG_ABBREVIATIONS, json.dumps(self.abbreviations))


    def _init_db_tables(self, config):
        """ Set up the word table and fill it with pre-computed word
            frequencies.
        """
        with connect(self.dsn) as conn:
            sqlp = SQLPreprocessor(conn, config)
            sqlp.run_sql_file(conn, 'tokenizer/legacy_tokenizer_tables.sql')
            conn.commit()

            LOG.warning("Precomputing word tokens")

            # get partial words and their frequencies
            words = Counter()
            with self.name_analyzer() as analyzer:
                with conn.cursor(name="words") as cur:
                    cur.execute("SELECT svals(name) as v, count(*) FROM place GROUP BY v")

                    for name, cnt in cur:
                        term = analyzer.make_standard_word(name)
                        if term:
                            for word in term.split():
                                words[word] += cnt

            # copy them back into the word table
            copystr = io.StringIO(''.join(('{}\t{}\n'.format(*args) for args in words.items())))


            with conn.cursor() as cur:
                copystr.seek(0)
                cur.copy_from(copystr, 'word', columns=['word_token', 'search_name_count'])
                cur.execute("""UPDATE word SET word_id = nextval('seq_word')
                               WHERE word_id is null""")

            conn.commit()


class LegacyICUNameAnalyzer:
    """ The legacy analyzer uses the ICU library for splitting names.

        Each instance opens a connection to the database to request the
        normalization.
    """

    def __init__(self, dsn, normalizer, transliterator, abbreviations):
        self.conn = connect(dsn).connection
        self.conn.autocommit = True
        self.normalizer = normalizer
        self.transliterator = transliterator
        self.abbreviations = abbreviations

        self._cache = _TokenCache()


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


    def close(self):
        """ Free all resources used by the analyzer.
        """
        if self.conn:
            self.conn.close()
            self.conn = None


    def get_word_token_info(self, conn, words):
        """ Return token information for the given list of words.
            If a word starts with # it is assumed to be a full name
            otherwise is a partial name.

            The function returns a list of tuples with
            (original word, word token, word id).

            The function is used for testing and debugging only
            and not necessarily efficient.
        """
        tokens = {}
        for word in words:
            if word.startswith('#'):
                tokens[word] = ' ' + self.make_standard_word(word[1:])
            else:
                tokens[word] = self.make_standard_word(word)

        with conn.cursor() as cur:
            cur.execute("""SELECT word_token, word_id
                           FROM word, (SELECT unnest(%s::TEXT[]) as term) t
                           WHERE word_token = t.term
                                 and class is null and country_code is null""",
                        (list(tokens.values()), ))
            ids = {r[0]: r[1] for r in cur}

        return [(k, v, ids[v]) for k, v in tokens.items()]


    def normalize(self, phrase):
        """ Normalize the given phrase, i.e. remove all properties that
            are irrelevant for search.
        """
        return self.normalizer.transliterate(phrase)

    @staticmethod
    def normalize_postcode(postcode):
        """ Convert the postcode to a standardized form.

            This function must yield exactly the same result as the SQL function
            'token_normalized_postcode()'.
        """
        return postcode.strip().upper()


    @functools.lru_cache(maxsize=1024)
    def make_standard_word(self, name):
        """ Create the normalised version of the input.
        """
        norm = ' ' + self.transliterator.transliterate(name) + ' '
        for full, abbr in self.abbreviations:
            if full in norm:
                norm = norm.replace(full, abbr)

        return norm.strip()


    def _make_standard_hnr(self, hnr):
        """ Create a normalised version of a housenumber.

            This function takes minor shortcuts on transliteration.
        """
        if hnr.isdigit():
            return hnr

        return self.transliterator.transliterate(hnr)

    def update_postcodes_from_db(self):
        """ Update postcode tokens in the word table from the location_postcode
            table.
        """
        to_delete = []
        copystr = io.StringIO()
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

            for postcode, word in cur:
                if postcode is None:
                    to_delete.append(word)
                else:
                    copystr.write(postcode)
                    copystr.write('\t ')
                    copystr.write(self.transliterator.transliterate(postcode))
                    copystr.write('\tplace\tpostcode\t0\n')

            if to_delete:
                cur.execute("""DELETE FROM WORD
                               WHERE class ='place' and type = 'postcode'
                                     and word = any(%s)
                            """, (to_delete, ))

            if copystr.getvalue():
                copystr.seek(0)
                cur.copy_from(copystr, 'word',
                              columns=['word', 'word_token', 'class', 'type',
                                       'search_name_count'])


    def update_special_phrases(self, phrases, should_replace):
        """ Replace the search index for special phrases with the new phrases.
        """
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
                copystr = io.StringIO()
                for word, cls, typ, oper in to_add:
                    term = self.make_standard_word(word)
                    if term:
                        copystr.write(word)
                        copystr.write('\t ')
                        copystr.write(term)
                        copystr.write('\t')
                        copystr.write(cls)
                        copystr.write('\t')
                        copystr.write(typ)
                        copystr.write('\t')
                        copystr.write(oper if oper in ('in', 'near')  else '\\N')
                        copystr.write('\t0\n')

                copystr.seek(0)
                cur.copy_from(copystr, 'word',
                              columns=['word', 'word_token', 'class', 'type',
                                       'operator', 'search_name_count'])

            if to_delete and should_replace:
                psycopg2.extras.execute_values(
                    cur,
                    """ DELETE FROM word USING (VALUES %s) as v(name, in_class, in_type, op)
                        WHERE word = name and class = in_class and type = in_type
                              and ((op = '-' and operator is null) or op = operator)""",
                    to_delete)

        LOG.info("Total phrases: %s. Added: %s. Deleted: %s",
                 len(norm_phrases), len(to_add), len(to_delete))


    def add_country_names(self, country_code, names):
        """ Add names for the given country to the search index.
        """
        full_names = set((self.make_standard_word(n) for n in names))
        full_names.discard('')
        self._add_normalized_country_names(country_code, full_names)


    def _add_normalized_country_names(self, country_code, names):
        """ Add names for the given country to the search index.
        """
        word_tokens = set((' ' + name for name in names))
        with self.conn.cursor() as cur:
            # Get existing names
            cur.execute("SELECT word_token FROM word WHERE country_code = %s",
                        (country_code, ))
            word_tokens.difference_update((t[0] for t in cur))

            if word_tokens:
                cur.execute("""INSERT INTO word (word_id, word_token, country_code,
                                                 search_name_count)
                               (SELECT nextval('seq_word'), token, '{}', 0
                                FROM unnest(%s) as token)
                            """.format(country_code), (list(word_tokens),))


    def process_place(self, place):
        """ Determine tokenizer information about the given place.

            Returns a JSON-serialisable structure that will be handed into
            the database via the token_info field.
        """
        token_info = _TokenInfo(self._cache)

        names = place.get('name')

        if names:
            full_names = set((self.make_standard_word(name) for name in names.values()))
            full_names.discard('')

            token_info.add_names(self.conn, full_names)

            country_feature = place.get('country_feature')
            if country_feature and re.fullmatch(r'[A-Za-z][A-Za-z]', country_feature):
                self._add_normalized_country_names(country_feature.lower(),
                                                   full_names)

        address = place.get('address')

        if address:
            hnrs = []
            addr_terms = []
            for key, value in address.items():
                if key == 'postcode':
                    self._add_postcode(value)
                elif key in ('housenumber', 'streetnumber', 'conscriptionnumber'):
                    hnrs.append(value)
                elif key == 'street':
                    token_info.add_street(self.conn, self.make_standard_word(value))
                elif key == 'place':
                    token_info.add_place(self.conn, self.make_standard_word(value))
                elif not key.startswith('_') and \
                     key not in ('country', 'full'):
                    addr_terms.append((key, self.make_standard_word(value)))

            if hnrs:
                hnrs = self._split_housenumbers(hnrs)
                token_info.add_housenumbers(self.conn, [self._make_standard_hnr(n) for n in hnrs])

            if addr_terms:
                token_info.add_address_terms(self.conn, addr_terms)

        return token_info.data


    def _add_postcode(self, postcode):
        """ Make sure the normalized postcode is present in the word table.
        """
        if re.search(r'[:,;]', postcode) is None:
            postcode = self.normalize_postcode(postcode)

            if postcode not in self._cache.postcodes:
                term = self.make_standard_word(postcode)
                if not term:
                    return

                with self.conn.cursor() as cur:
                    # no word_id needed for postcodes
                    cur.execute("""INSERT INTO word (word, word_token, class, type,
                                                     search_name_count)
                                   (SELECT pc, %s, 'place', 'postcode', 0
                                    FROM (VALUES (%s)) as v(pc)
                                    WHERE NOT EXISTS
                                     (SELECT * FROM word
                                      WHERE word = pc and class='place' and type='postcode'))
                                """, (' ' + term, postcode))
                self._cache.postcodes.add(postcode)

    @staticmethod
    def _split_housenumbers(hnrs):
        if len(hnrs) > 1 or ',' in hnrs[0] or ';' in hnrs[0]:
            # split numbers if necessary
            simple_list = []
            for hnr in hnrs:
                simple_list.extend((x.strip() for x in re.split(r'[;,]', hnr)))

            if len(simple_list) > 1:
                hnrs = list(set(simple_list))
            else:
                hnrs = simple_list

        return hnrs




class _TokenInfo:
    """ Collect token information to be sent back to the database.
    """
    def __init__(self, cache):
        self.cache = cache
        self.data = {}

    @staticmethod
    def _mk_array(tokens):
        return '{%s}' % ','.join((str(s) for s in tokens))


    def add_names(self, conn, names):
        """ Adds token information for the normalised names.
        """
        # Start with all partial names
        terms = set((part for ns in names for part in ns.split()))
        # Add partials for the full terms (TO BE REMOVED)
        terms.update((n for n in names))
        # Add the full names
        terms.update((' ' + n for n in names))

        self.data['names'] = self._mk_array(self.cache.get_term_tokens(conn, terms))


    def add_housenumbers(self, conn, hnrs):
        """ Extract housenumber information from a list of normalised
            housenumbers.
        """
        self.data['hnr_tokens'] = self._mk_array(self.cache.get_hnr_tokens(conn, hnrs))
        self.data['hnr'] = ';'.join(hnrs)


    def add_street(self, conn, street):
        """ Add addr:street match terms.
        """
        if not street:
            return

        term = ' ' + street

        tid = self.cache.names.get(term)

        if tid is None:
            with conn.cursor() as cur:
                cur.execute("""SELECT word_id FROM word
                                WHERE word_token = %s
                                      and class is null and type is null""",
                            (term, ))
                if cur.rowcount > 0:
                    tid = cur.fetchone()[0]
                    self.cache.names[term] = tid

        if tid is not None:
            self.data['street'] = '{%d}' % tid


    def add_place(self, conn, place):
        """ Add addr:place search and match terms.
        """
        if not place:
            return

        partial_ids = self.cache.get_term_tokens(conn, place.split())
        tid = self.cache.get_term_tokens(conn, [' ' + place])

        self.data['place_search'] = self._mk_array(itertools.chain(partial_ids, tid))
        self.data['place_match'] = '{%s}' % tid[0]


    def add_address_terms(self, conn, terms):
        """ Add additional address terms.
        """
        tokens = {}

        for key, value in terms:
            if not value:
                continue
            partial_ids = self.cache.get_term_tokens(conn, value.split())
            term = ' ' + value
            tid = self.cache.names.get(term)

            if tid is None:
                with conn.cursor() as cur:
                    cur.execute("""SELECT word_id FROM word
                                    WHERE word_token = %s
                                          and class is null and type is null""",
                                (term, ))
                    if cur.rowcount > 0:
                        tid = cur.fetchone()[0]
                        self.cache.names[term] = tid

            tokens[key] = [self._mk_array(partial_ids),
                           '{%s}' % ('' if tid is None else str(tid))]

        if tokens:
            self.data['addr'] = tokens


class _TokenCache:
    """ Cache for token information to avoid repeated database queries.

        This cache is not thread-safe and needs to be instantiated per
        analyzer.
    """
    def __init__(self):
        self.names = {}
        self.postcodes = set()
        self.housenumbers = {}


    def get_term_tokens(self, conn, terms):
        """ Get token ids for a list of terms, looking them up in the database
            if necessary.
        """
        tokens = []
        askdb = []

        for term in terms:
            token = self.names.get(term)
            if token is None:
                askdb.append(term)
            elif token != 0:
                tokens.append(token)

        if askdb:
            with conn.cursor() as cur:
                cur.execute("SELECT term, getorcreate_term_id(term) FROM unnest(%s) as term",
                            (askdb, ))
                for term, tid in cur:
                    self.names[term] = tid
                    if tid != 0:
                        tokens.append(tid)

        return tokens


    def get_hnr_tokens(self, conn, terms):
        """ Get token ids for a list of housenumbers, looking them up in the
            database if necessary.
        """
        tokens = []
        askdb = []

        for term in terms:
            token = self.housenumbers.get(term)
            if token is None:
                askdb.append(term)
            else:
                tokens.append(token)

        if askdb:
            with conn.cursor() as cur:
                cur.execute("SELECT nr, getorcreate_hnr_id(nr) FROM unnest(%s) as nr",
                            (askdb, ))
                for term, tid in cur:
                    self.housenumbers[term] = tid
                    tokens.append(tid)

        return tokens
