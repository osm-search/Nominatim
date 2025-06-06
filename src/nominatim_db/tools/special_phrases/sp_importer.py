# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
    Module containing the class handling the import
    of the special phrases.

    Phrases are analyzed and imported into the database.

    The phrases already present in the database which are not
    valids anymore are removed.
"""
from typing import Iterable, Tuple, Mapping, Sequence, Optional, Set
import logging
import re
from psycopg.sql import Identifier, SQL

from ...typing import Protocol
from ...config import Configuration
from ...db.connection import Connection, drop_tables, index_exists
from .importer_statistics import SpecialPhrasesImporterStatistics
from .special_phrase import SpecialPhrase
from ...tokenizer.base import AbstractTokenizer

LOG = logging.getLogger()


def _classtype_table(phrase_class: str, phrase_type: str) -> str:
    """ Return the name of the table for the given class and type.
    """
    return f'place_classtype_{phrase_class}_{phrase_type}'


class SpecialPhraseLoader(Protocol):
    """ Protocol for classes implementing a loader for special phrases.
    """

    def generate_phrases(self) -> Iterable[SpecialPhrase]:
        """ Generates all special phrase terms this loader can produce.
        """


class SPImporter():
    """
        Class handling the process of special phrases importation into the database.

        Take a sp loader which load the phrases from an external source.
    """
    def __init__(self, config: Configuration, conn: Connection,
                 sp_loader: SpecialPhraseLoader) -> None:
        self.config = config
        self.db_connection = conn
        self.sp_loader = sp_loader
        self.statistics_handler = SpecialPhrasesImporterStatistics()
        self.black_list, self.white_list = self._load_white_and_black_lists()
        self.sanity_check_pattern = re.compile(r'^\w+$')
        # This set will contain all existing phrases to be added.
        # It contains tuples with the following format: (label, class, type, operator)
        self.word_phrases: Set[Tuple[str, str, str, str]] = set()
        # This set will contain all existing place_classtype tables which doesn't match any
        # special phrases class/type on the wiki.
        self.table_phrases_to_delete: Set[str] = set()

    def get_classtype_pairs(self, min: int = 0) -> Set[Tuple[str, str]]:
        """
            Returns list of allowed special phrases from the database,
            restricting to a list of combinations of classes and types
            which occur equal to or more than a specified amount of times.

            Default value for this is 0, which allows everything in database.
        """
        db_combinations = set()

        query = f"""
        SELECT class AS CLS, type AS typ
        FROM placex
        GROUP BY class, type
        HAVING COUNT(*) >= {min}
        """

        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL(query))
            for row in db_cursor:
                db_combinations.add((row[0], row[1]))

        return db_combinations

    def import_phrases(self, tokenizer: AbstractTokenizer, should_replace: bool,
                       min: int = 0) -> None:
        """
            Iterate through all SpecialPhrases extracted from the
            loader and import them into the database.

            If should_replace is set to True only the loaded phrases
            will be kept into the database. All other phrases already
            in the database will be removed.
        """
        LOG.warning('Special phrases importation starting')
        self._fetch_existing_place_classtype_tables()

        # Store pairs of class/type for further processing
        class_type_pairs = set()

        for phrase in self.sp_loader.generate_phrases():
            result = self._process_phrase(phrase)
            if result:
                class_type_pairs.add(result)

        self._create_classtype_table_and_indexes(class_type_pairs, min)
        if should_replace:
            self._remove_non_existent_tables_from_db()

        self.db_connection.commit()

        with tokenizer.name_analyzer() as analyzer:
            analyzer.update_special_phrases(self.word_phrases, should_replace)

        LOG.warning('Import done.')
        self.statistics_handler.notify_import_done()

    def _fetch_existing_place_classtype_tables(self) -> None:
        """
            Fetch existing place_classtype tables.
            Fill the table_phrases_to_delete set of the class.
        """
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            AND table_name like 'place_classtype_%';
        """
        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL(query))
            for row in db_cursor:
                self.table_phrases_to_delete.add(row[0])

    def _load_white_and_black_lists(self) \
            -> Tuple[Mapping[str, Sequence[str]], Mapping[str, Sequence[str]]]:
        """
            Load white and black lists from phrases-settings.json.
        """
        settings = self.config.load_sub_configuration('phrase-settings.json')

        return settings['blackList'], settings['whiteList']

    def _check_sanity(self, phrase: SpecialPhrase) -> bool:
        """
            Check sanity of given inputs in case somebody added garbage in the wiki.
            If a bad class/type is detected the system will exit with an error.
        """
        class_matchs = self.sanity_check_pattern.findall(phrase.p_class)
        type_matchs = self.sanity_check_pattern.findall(phrase.p_type)

        if not class_matchs or not type_matchs:
            LOG.warning("Bad class/type: %s=%s. It will not be imported",
                        phrase.p_class, phrase.p_type)
            return False
        return True

    def _process_phrase(self, phrase: SpecialPhrase) -> Optional[Tuple[str, str]]:
        """
            Processes the given phrase by checking black and white list
            and sanity.
            Return the class/type pair corresponding to the phrase.
        """

        # blacklisting: disallow certain class/type combinations
        if phrase.p_class in self.black_list.keys() \
           and phrase.p_type in self.black_list[phrase.p_class]:
            return None

        # whitelisting: if class is in whitelist, allow only tags in the list
        if phrase.p_class in self.white_list.keys() \
           and phrase.p_type not in self.white_list[phrase.p_class]:
            return None

        # sanity check, in case somebody added garbage in the wiki
        if not self._check_sanity(phrase):
            self.statistics_handler.notify_one_phrase_invalid()
            return None

        self.word_phrases.add((phrase.p_label, phrase.p_class,
                               phrase.p_type, phrase.p_operator))

        return (phrase.p_class, phrase.p_type)

    def _create_classtype_table_and_indexes(self,
                                            class_type_pairs: Iterable[Tuple[str, str]],
                                            min: int = 0) -> None:
        """
            Create table place_classtype for each given pair.
            Also create indexes on place_id and centroid.
        """
        LOG.warning('Create tables and indexes...')

        sql_tablespace = self.config.TABLESPACE_AUX_DATA
        if sql_tablespace:
            sql_tablespace = ' TABLESPACE ' + sql_tablespace

        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute("CREATE INDEX idx_placex_classtype ON placex (class, type)")

        if min:
            allowed_special_phrases = self.get_classtype_pairs(min)

        for pair in class_type_pairs:
            phrase_class = pair[0]
            phrase_type = pair[1]

            # Will only filter if min is not 0
            if min and (phrase_class, phrase_type) not in allowed_special_phrases:
                LOG.warning("Skipping phrase %s=%s: not in allowed special phrases",
                            phrase_class, phrase_type)
                continue

            table_name = _classtype_table(phrase_class, phrase_type)

            if table_name in self.table_phrases_to_delete:
                self.statistics_handler.notify_one_table_ignored()
                # Remove this table from the ones to delete as it match a
                # class/type still existing on the special phrases of the wiki.
                self.table_phrases_to_delete.remove(table_name)
                # So don't need to create the table and indexes.
                continue

            # Table creation
            self._create_place_classtype_table(sql_tablespace, phrase_class, phrase_type)

            # Indexes creation
            self._create_place_classtype_indexes(sql_tablespace, phrase_class, phrase_type)

            # Grant access on read to the web user.
            self._grant_access_to_webuser(phrase_class, phrase_type)

            self.statistics_handler.notify_one_table_created()

        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute("DROP INDEX idx_placex_classtype")

    def _create_place_classtype_table(self, sql_tablespace: str,
                                      phrase_class: str, phrase_type: str) -> None:
        """
            Create table place_classtype of the given phrase_class/phrase_type
            if doesn't exit.
        """
        table_name = _classtype_table(phrase_class, phrase_type)
        with self.db_connection.cursor() as cur:
            cur.execute(SQL("""CREATE TABLE IF NOT EXISTS {} {} AS
                                 SELECT place_id AS place_id,
                                        st_centroid(geometry) AS centroid
                                 FROM placex
                                 WHERE class = %s AND type = %s
                             """).format(Identifier(table_name), SQL(sql_tablespace)),
                        (phrase_class, phrase_type))

    def _create_place_classtype_indexes(self, sql_tablespace: str,
                                        phrase_class: str, phrase_type: str) -> None:
        """
            Create indexes on centroid and place_id for the place_classtype table.
        """
        index_prefix = f'idx_place_classtype_{phrase_class}_{phrase_type}_'
        base_table = _classtype_table(phrase_class, phrase_type)
        # Index on centroid
        if not index_exists(self.db_connection, index_prefix + 'centroid'):
            with self.db_connection.cursor() as db_cursor:
                db_cursor.execute(SQL("CREATE INDEX {} ON {} USING GIST (centroid) {}")
                                  .format(Identifier(index_prefix + 'centroid'),
                                          Identifier(base_table),
                                          SQL(sql_tablespace)))

        # Index on place_id
        if not index_exists(self.db_connection, index_prefix + 'place_id'):
            with self.db_connection.cursor() as db_cursor:
                db_cursor.execute(SQL("CREATE INDEX {} ON {} USING btree(place_id) {}")
                                  .format(Identifier(index_prefix + 'place_id'),
                                          Identifier(base_table),
                                          SQL(sql_tablespace)))

    def _grant_access_to_webuser(self, phrase_class: str, phrase_type: str) -> None:
        """
            Grant access on read to the table place_classtype for the webuser.
        """
        table_name = _classtype_table(phrase_class, phrase_type)
        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL("""GRANT SELECT ON {} TO {}""")
                              .format(Identifier(table_name),
                                      Identifier(self.config.DATABASE_WEBUSER)))

    def _remove_non_existent_tables_from_db(self) -> None:
        """
            Remove special phrases which doesn't exist on the wiki anymore.
            Delete the place_classtype tables.
        """
        LOG.warning('Cleaning database...')

        # Delete place_classtype tables corresponding to class/type which
        # are not on the wiki anymore.
        drop_tables(self.db_connection, *self.table_phrases_to_delete)
        for _ in self.table_phrases_to_delete:
            self.statistics_handler.notify_one_table_deleted()
