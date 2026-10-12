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
from typing import Iterable, Tuple, Mapping, Sequence, Set, Protocol
import logging
import re

from ...config import Configuration
from ...db.connection import Connection
from .importer_statistics import SpecialPhrasesImporterStatistics
from .special_phrase import SpecialPhrase
from ...tokenizer.base import AbstractTokenizer

LOG = logging.getLogger()


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

    def import_phrases(self, tokenizer: AbstractTokenizer, should_replace: bool) -> None:
        """
            Iterate through all SpecialPhrases extracted from the
            loader and import them into the database.

            If should_replace is set to True only the loaded phrases
            will be kept into the database. All other phrases already
            in the database will be removed.
        """
        LOG.warning('Special phrases importation starting')

        for phrase in self.sp_loader.generate_phrases():
            self._process_phrase(phrase)

        self.db_connection.commit()

        with tokenizer.name_analyzer() as analyzer:
            analyzer.update_special_phrases(self.word_phrases, should_replace)

        LOG.warning('Import done.')
        self.statistics_handler.notify_import_done()

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

    def _process_phrase(self, phrase: SpecialPhrase) -> None:
        """
            Processes the given phrase by checking black and white list
            and sanity, and adds it to the phrases to import.
        """

        # blacklisting: disallow certain class/type combinations
        if phrase.p_class in self.black_list.keys() \
           and phrase.p_type in self.black_list[phrase.p_class]:
            return

        # whitelisting: if class is in whitelist, allow only tags in the list
        if phrase.p_class in self.white_list.keys() \
           and phrase.p_type not in self.white_list[phrase.p_class]:
            return

        # sanity check, in case somebody added garbage in the wiki
        if not self._check_sanity(phrase):
            self.statistics_handler.notify_one_phrase_invalid()
            return

        self.word_phrases.add((phrase.p_label, phrase.p_class,
                               phrase.p_type, phrase.p_operator))
