# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
from typing import Optional, Any, cast, Sequence, Iterable, Mapping
import logging

from psycopg.types.json import Jsonb

from ...db.connection import connect, Connection, Cursor, execute_scalar
from ...data.place_info import PlaceInfo
from ...data.place_name import PlaceName, PlaceNames
from ..base import AbstractAnalyzer
from .token_analysis import ICUTokenAnalysis
from . import icu_types as itype

LOG = logging.getLogger()


class ICUNameAnalyzer(AbstractAnalyzer):
    """ The ICU analyzer uses the ICU library for splitting names.

        Each instance opens a connection to the database to request the
        normalization.
    """

    def __init__(self, dsn: str, token_analysis: ICUTokenAnalysis) -> None:
        self.conn: Optional[Connection] = connect(dsn)
        self.conn.autocommit = True
        self.token_analysis = token_analysis

        self._cache = itype.TokenCache()

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

    def get_word_token_info(self, words: Sequence[str]) -> list[tuple[str, str, Optional[int]]]:
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

    def update_special_phrases(self, phrases: Iterable[tuple[str, str, str, str]],
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
                             new_phrases: set[tuple[str, str, str, str]],
                             existing_phrases: set[tuple[str, str, str, str]]) -> int:
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
                                new_phrases: set[tuple[str, str, str, str]],
                                existing_phrases: set[tuple[str, str, str, str]]) -> int:
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

    def add_country_names(self, country_code: str, names: PlaceNames) -> None:
        """ Add default names for the given country to the search index.
        """
        self._add_country_full_names(country_code, names, internal=True)

    def _add_country_full_names(self, country_code: str, names: PlaceNames,
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
            existing_tokens: dict[bool, set[tuple[str, str]]] = {True: set(), False: set()}
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

        if place.searchable_names:
            token_info.set_names(self._compute_name_tokens(place.searchable_names))

            if place.is_country():
                assert place.country_code is not None
                self._add_country_full_names(place.country_code, place.searchable_names)

        if place.searchable_address:
            self._process_place_address(token_info, place.searchable_address)

        return token_info.to_dict()

    def _process_place_address(self, token_info: '_TokenInfo', address: PlaceNames) -> None:
        for item in address:
            if item.kind == 'postcode':
                token_info.set_postcode(self.normalize_postcode(item.name))
            elif item.kind == 'housenumber':
                token_info.add_housenumber(self._compute_housenumber_token(item))
            elif item.kind == 'street':
                token_info.add_street(self._retrieve_full_tokens(item.name))
            elif item.kind == 'place':
                if not item.suffix:
                    token_info.add_place(self._compute_name_tokens([item]))
            elif (not item.kind.startswith('_') and not item.suffix and
                  item.kind not in ('country', 'full', 'inclusion')):
                token_info.add_address_term(item.kind,
                                            self._compute_name_tokens([item]))

    def _compute_housenumber_token(self, hnr: PlaceName) -> Optional[itype.HousenumberTokenInfo]:
        """ Normalize the housenumber and return the word token and the
            canonical form.
        """
        assert self.conn is not None
        analyzer = self.token_analysis.analysis.get('@housenumber')
        result = None

        if analyzer is None:
            # When no custom analyzer is set, simply normalize and transliterate
            norm_name = self._search_normalized(hnr.name)
            if norm_name:
                result = self._cache.housenumbers.get(norm_name)
                if result is None:
                    hid = execute_scalar(self.conn, "SELECT getorcreate_hnr_id(%s)", (norm_name, ))

                    result = itype.HousenumberTokenInfo(hid, norm_name)
                    self._cache.housenumbers[norm_name] = result
        else:
            # Otherwise use the analyzer to determine the canonical name.
            # Per convention we use the first variant as the 'lookup name', the
            # name that gets saved in the housenumber field of the place.
            word_id = analyzer.get_canonical_id(hnr)
            if word_id:
                result = self._cache.housenumbers.get(word_id)
                if result is None:
                    varout = analyzer.compute_variants(word_id)
                    if isinstance(varout, tuple):
                        variants = varout[0]
                    else:
                        variants = varout
                    if variants:
                        hid = execute_scalar(self.conn, "SELECT create_analyzed_hnr_id(%s, %s)",
                                             (word_id, variants))
                        result = itype.HousenumberTokenInfo(hid, variants[0])
                        self._cache.housenumbers[word_id] = result

        return result

    def _retrieve_full_tokens(self, name: str) -> list[int]:
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

    def _compute_name_tokens(self, names: PlaceNames) -> set[int]:
        """ Computes the full name and partial name tokens for the given
            dictionary of names.
        """
        assert self.conn is not None
        out = set()

        for name in names:
            analyzer_id = name.get_attr('analyzer')
            is_partial = name.get_attr('partial')
            analyzer = self.token_analysis.get_analyzer(analyzer_id)
            word_id = analyzer.get_canonical_id(name)
            if analyzer_id is None:
                token_id = word_id
            else:
                token_id = f'{word_id}@{analyzer_id}'
            if is_partial:
                token_id += '@@part'

            tokens = self._cache.names.get(token_id)
            if tokens is None:
                varset = analyzer.compute_variants(word_id)
                if isinstance(varset, tuple):
                    variants, lookups = varset
                else:
                    variants, lookups = varset, None
                if not variants:
                    continue

                with self.conn.cursor() as cur:
                    if is_partial:
                        cur.execute("SELECT * FROM getorcreate_partial_words(%s)",
                                    (variants,))
                    else:
                        cur.execute("""SELECT partial_tokens || full_token
                                       FROM getorcreate_full_word(%s, %s, %s)""",
                                    (token_id, variants, lookups))

                    tokens = cast(tuple[list[int]], cur.fetchone())[0]

                self._cache.names[token_id] = tokens

            out.update(tokens)

        return out


def _mk_array(tokens: Iterable[Any]) -> str:
    """ Create an array string suitable for Postgres array input.
    """
    return '{' + ','.join((str(s) for s in tokens)) + '}'


class _TokenInfo:
    """ Collect token information to be sent back to the database.
    """
    def __init__(self) -> None:
        self.names: Optional[str] = None
        self.housenumbers: set[str] = set()
        self.housenumber_tokens: set[int] = set()
        self.street_tokens: Optional[set[int]] = None
        self.place_tokens: set[int] = set()
        self.address_tokens: dict[str, str] = {}
        self.postcode: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """ Return the token information in database importable format.
        """
        out: dict[str, Any] = {}

        if self.names:
            out['names'] = self.names

        if self.housenumbers:
            out['hnr'] = ';'.join(self.housenumbers)
            out['hnr_tokens'] = _mk_array(self.housenumber_tokens)

        if self.street_tokens is not None:
            out['street'] = _mk_array(self.street_tokens)

        if self.place_tokens:
            out['place'] = _mk_array(self.place_tokens)

        if self.address_tokens:
            out['addr'] = self.address_tokens

        if self.postcode:
            out['postcode'] = self.postcode

        return out

    def set_names(self, tokens: Iterable[int]) -> None:
        """ Adds token information for the normalised names.
        """
        self.names = _mk_array(tokens)

    def add_housenumber(self, token_info: Optional[itype.HousenumberTokenInfo]) -> None:
        """ Extract housenumber information from a list of normalised
            housenumbers.
        """
        if token_info:
            self.housenumbers.add(token_info.housenumber)
            self.housenumber_tokens.add(token_info.token)

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
        array = _mk_array(partials)
        if len(array) > 2:
            self.address_tokens[key] = array

    def set_postcode(self, postcode: Optional[str]) -> None:
        """ Set the postcode to the given one.
        """
        self.postcode = postcode
