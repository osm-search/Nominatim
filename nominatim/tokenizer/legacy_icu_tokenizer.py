"""
Tokenizer implementing normalisation as used before Nominatim 4 but using
libICU instead of the PostgreSQL module.
"""
from collections import Counter
import itertools
import logging
import re
from textwrap import dedent
from pathlib import Path

import psycopg2.extras

from nominatim.db.connection import connect
from nominatim.db.properties import set_property, get_property
from nominatim.db.utils import CopyBuffer
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.tokenizer.icu_rule_loader import ICURuleLoader
from nominatim.tokenizer.icu_name_processor import ICUNameProcessor, ICUNameProcessorRules

DBCFG_MAXWORDFREQ = "tokenizer_maxwordfreq"
DBCFG_TERM_NORMALIZATION = "tokenizer_term_normalization"

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
        self.naming_rules = None
        self.term_normalization = None
        self.max_word_frequency = None


    def init_new_db(self, config, init_db=True):
        """ Set up a new tokenizer for the database.

            This copies all necessary data in the project directory to make
            sure the tokenizer remains stable even over updates.
        """
        if config.TOKENIZER_CONFIG:
            cfgfile = Path(config.TOKENIZER_CONFIG)
        else:
            cfgfile = config.config_dir / 'legacy_icu_tokenizer.yaml'

        loader = ICURuleLoader(cfgfile)
        self.naming_rules = ICUNameProcessorRules(loader=loader)
        self.term_normalization = config.TERM_NORMALIZATION
        self.max_word_frequency = config.MAX_WORD_FREQUENCY

        self._install_php(config.lib_dir.php)
        self._save_config(config)

        if init_db:
            self.update_sql_functions(config)
            self._init_db_tables(config)


    def init_from_project(self):
        """ Initialise the tokenizer from the project directory.
        """
        with connect(self.dsn) as conn:
            self.naming_rules = ICUNameProcessorRules(conn=conn)
            self.term_normalization = get_property(conn, DBCFG_TERM_NORMALIZATION)
            self.max_word_frequency = get_property(conn, DBCFG_MAXWORDFREQ)


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

        if self.naming_rules is None:
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
        return LegacyICUNameAnalyzer(self.dsn, ICUNameProcessor(self.naming_rules))


    def _install_php(self, phpdir):
        """ Install the php script for the tokenizer.
        """
        php_file = self.data_dir / "tokenizer.php"
        php_file.write_text(dedent("""\
            <?php
            @define('CONST_Max_Word_Frequency', {0.max_word_frequency});
            @define('CONST_Term_Normalization_Rules', "{0.term_normalization}");
            @define('CONST_Transliteration', "{0.naming_rules.search_rules}");
            require_once('{1}/tokenizer/legacy_icu_tokenizer.php');
            """.format(self, phpdir))) # pylint: disable=missing-format-attribute


    def _save_config(self, config):
        """ Save the configuration that needs to remain stable for the given
            database as database properties.
        """
        with connect(self.dsn) as conn:
            self.naming_rules.save_rules(conn)

            set_property(conn, DBCFG_MAXWORDFREQ, config.MAX_WORD_FREQUENCY)
            set_property(conn, DBCFG_TERM_NORMALIZATION, self.term_normalization)


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
            name_proc = ICUNameProcessor(self.naming_rules)
            with conn.cursor(name="words") as cur:
                cur.execute("SELECT svals(name) as v, count(*) FROM place GROUP BY v")

                for name, cnt in cur:
                    for word in name_proc.get_variants_ascii(name_proc.get_normalized(name)):
                        for term in word.split():
                            words[term] += cnt

            # copy them back into the word table
            with CopyBuffer() as copystr:
                for args in words.items():
                    copystr.add(*args)

                with conn.cursor() as cur:
                    copystr.copy_out(cur, 'word',
                                     columns=['word_token', 'search_name_count'])
                    cur.execute("""UPDATE word SET word_id = nextval('seq_word')
                                   WHERE word_id is null""")

            conn.commit()


class LegacyICUNameAnalyzer:
    """ The legacy analyzer uses the ICU library for splitting names.

        Each instance opens a connection to the database to request the
        normalization.
    """

    def __init__(self, dsn, name_proc):
        self.conn = connect(dsn).connection
        self.conn.autocommit = True
        self.name_processor = name_proc

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


    def get_word_token_info(self, words):
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
                tokens[word] = ' ' + self.name_processor.get_search_normalized(word[1:])
            else:
                tokens[word] = self.name_processor.get_search_normalized(word)

        with self.conn.cursor() as cur:
            cur.execute("""SELECT word_token, word_id
                           FROM word, (SELECT unnest(%s::TEXT[]) as term) t
                           WHERE word_token = t.term
                                 and class is null and country_code is null""",
                        (list(tokens.values()), ))
            ids = {r[0]: r[1] for r in cur}

        return [(k, v, ids.get(v, None)) for k, v in tokens.items()]


    @staticmethod
    def normalize_postcode(postcode):
        """ Convert the postcode to a standardized form.

            This function must yield exactly the same result as the SQL function
            'token_normalized_postcode()'.
        """
        return postcode.strip().upper()


    def _make_standard_hnr(self, hnr):
        """ Create a normalised version of a housenumber.

            This function takes minor shortcuts on transliteration.
        """
        return self.name_processor.get_search_normalized(hnr)

    def update_postcodes_from_db(self):
        """ Update postcode tokens in the word table from the location_postcode
            table.
        """
        to_delete = []
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

            with CopyBuffer() as copystr:
                for postcode, word in cur:
                    if postcode is None:
                        to_delete.append(word)
                    else:
                        copystr.add(
                            postcode,
                            ' ' + self.name_processor.get_search_normalized(postcode),
                            'place', 'postcode', 0)

                if to_delete:
                    cur.execute("""DELETE FROM WORD
                                   WHERE class ='place' and type = 'postcode'
                                         and word = any(%s)
                                """, (to_delete, ))

                copystr.copy_out(cur, 'word',
                                 columns=['word', 'word_token', 'class', 'type',
                                          'search_name_count'])


    def update_special_phrases(self, phrases, should_replace):
        """ Replace the search index for special phrases with the new phrases.
        """
        norm_phrases = set(((self.name_processor.get_normalized(p[0]), p[1], p[2], p[3])
                            for p in phrases))

        with self.conn.cursor() as cur:
            # Get the old phrases.
            existing_phrases = set()
            cur.execute("""SELECT word, class, type, operator FROM word
                           WHERE class != 'place'
                                 OR (type != 'house' AND type != 'postcode')""")
            for label, cls, typ, oper in cur:
                existing_phrases.add((label, cls, typ, oper or '-'))

            added = self._add_special_phrases(cur, norm_phrases, existing_phrases)
            if should_replace:
                deleted = self._remove_special_phrases(cur, norm_phrases,
                                                       existing_phrases)
            else:
                deleted = 0

        LOG.info("Total phrases: %s. Added: %s. Deleted: %s",
                 len(norm_phrases), added, deleted)


    def _add_special_phrases(self, cursor, new_phrases, existing_phrases):
        """ Add all phrases to the database that are not yet there.
        """
        to_add = new_phrases - existing_phrases

        added = 0
        with CopyBuffer() as copystr:
            for word, cls, typ, oper in to_add:
                term = self.name_processor.get_search_normalized(word)
                if term:
                    copystr.add(word, term, cls, typ,
                                oper if oper in ('in', 'near')  else None, 0)
                    added += 1

            copystr.copy_out(cursor, 'word',
                             columns=['word', 'word_token', 'class', 'type',
                                      'operator', 'search_name_count'])

        return added


    @staticmethod
    def _remove_special_phrases(cursor, new_phrases, existing_phrases):
        """ Remove all phrases from the databse that are no longer in the
            new phrase list.
        """
        to_delete = existing_phrases - new_phrases

        if to_delete:
            psycopg2.extras.execute_values(
                cursor,
                """ DELETE FROM word USING (VALUES %s) as v(name, in_class, in_type, op)
                    WHERE word = name and class = in_class and type = in_type
                          and ((op = '-' and operator is null) or op = operator)""",
                to_delete)

        return len(to_delete)


    def add_country_names(self, country_code, names):
        """ Add names for the given country to the search index.
        """
        word_tokens = set()
        for name in self._compute_full_names(names):
            if name:
                word_tokens.add(' ' + self.name_processor.get_search_normalized(name))

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
            fulls, partials = self._compute_name_tokens(names)

            token_info.add_names(fulls, partials)

            country_feature = place.get('country_feature')
            if country_feature and re.fullmatch(r'[A-Za-z][A-Za-z]', country_feature):
                self.add_country_names(country_feature.lower(), names)

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
                    token_info.add_street(*self._compute_name_tokens({'name': value}))
                elif key == 'place':
                    token_info.add_place(*self._compute_name_tokens({'name': value}))
                elif not key.startswith('_') and \
                     key not in ('country', 'full'):
                    addr_terms.append((key, *self._compute_name_tokens({'name': value})))

            if hnrs:
                hnrs = self._split_housenumbers(hnrs)
                token_info.add_housenumbers(self.conn, [self._make_standard_hnr(n) for n in hnrs])

            if addr_terms:
                token_info.add_address_terms(addr_terms)

        return token_info.data


    def _compute_name_tokens(self, names):
        """ Computes the full name and partial name tokens for the given
            dictionary of names.
        """
        full_names = self._compute_full_names(names)
        full_tokens = set()
        partial_tokens = set()

        for name in full_names:
            norm_name = self.name_processor.get_normalized(name)
            full, part = self._cache.names.get(norm_name, (None, None))
            if full is None:
                variants = self.name_processor.get_variants_ascii(norm_name)
                with self.conn.cursor() as cur:
                    cur.execute("SELECT (getorcreate_full_word(%s, %s)).*",
                                (norm_name, variants))
                    full, part = cur.fetchone()

                self._cache.names[norm_name] = (full, part)

            full_tokens.add(full)
            partial_tokens.update(part)

        return full_tokens, partial_tokens


    @staticmethod
    def _compute_full_names(names):
        """ Return the set of all full name word ids to be used with the
            given dictionary of names.
        """
        full_names = set()
        for name in (n for ns in names.values() for n in re.split('[;,]', ns)):
            full_names.add(name.strip())

            brace_idx = name.find('(')
            if brace_idx >= 0:
                full_names.add(name[:brace_idx].strip())

        return full_names


    def _add_postcode(self, postcode):
        """ Make sure the normalized postcode is present in the word table.
        """
        if re.search(r'[:,;]', postcode) is None:
            postcode = self.normalize_postcode(postcode)

            if postcode not in self._cache.postcodes:
                term = self.name_processor.get_search_normalized(postcode)
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
        self._cache = cache
        self.data = {}

    @staticmethod
    def _mk_array(tokens):
        return '{%s}' % ','.join((str(s) for s in tokens))


    def add_names(self, fulls, partials):
        """ Adds token information for the normalised names.
        """
        self.data['names'] = self._mk_array(itertools.chain(fulls, partials))


    def add_housenumbers(self, conn, hnrs):
        """ Extract housenumber information from a list of normalised
            housenumbers.
        """
        self.data['hnr_tokens'] = self._mk_array(self._cache.get_hnr_tokens(conn, hnrs))
        self.data['hnr'] = ';'.join(hnrs)


    def add_street(self, fulls, _):
        """ Add addr:street match terms.
        """
        if fulls:
            self.data['street'] = self._mk_array(fulls)


    def add_place(self, fulls, partials):
        """ Add addr:place search and match terms.
        """
        if fulls:
            self.data['place_search'] = self._mk_array(itertools.chain(fulls, partials))
            self.data['place_match'] = self._mk_array(fulls)


    def add_address_terms(self, terms):
        """ Add additional address terms.
        """
        tokens = {}

        for key, fulls, partials in terms:
            if fulls:
                tokens[key] = [self._mk_array(itertools.chain(fulls, partials)),
                               self._mk_array(fulls)]

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
