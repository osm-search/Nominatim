# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
    Module containing the SPWikiLoader class.
"""
from typing import Iterable
import re
import logging

from nominatim.config import Configuration
from nominatim.tools.special_phrases.special_phrase import SpecialPhrase
from nominatim.tools.exec_utils import get_url

LOG = logging.getLogger()

def _get_wiki_content(lang: str) -> str:
    """
        Request and return the wiki page's content
        corresponding to special phrases for a given lang.
        Requested URL Example :
            https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/EN
    """
    url = 'https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/' \
          + lang.upper()
    return get_url(url)


class SPWikiLoader:
    """
        Handles loading of special phrases from the wiki.
    """
    def __init__(self, config: Configuration) -> None:
        self.config = config
        # Compile the regex here to increase performances.
        self.occurence_pattern = re.compile(
            r'\| *([^\|]+) *\|\| *([^\|]+) *\|\| *([^\|]+) *\|\| *([^\|]+) *\|\| *([\-YN])'
        )
        # Hack around a bug where building=yes was imported with quotes into the wiki
        self.type_fix_pattern = re.compile(r'\"|&quot;')

        self.languages = self.config.get_str_list('LANGUAGES') or \
                         ['af', 'ar', 'br', 'ca', 'cs', 'de', 'en', 'es',
                          'et', 'eu', 'fa', 'fi', 'fr', 'gl', 'hr', 'hu',
                          'ia', 'is', 'it', 'ja', 'mk', 'nl', 'no', 'pl',
                          'ps', 'pt', 'ru', 'sk', 'sl', 'sv', 'uk', 'vi',
                          'lv', 'tr']


    def generate_phrases(self) -> Iterable[SpecialPhrase]:
        """ Download the wiki pages for the configured languages
            and extract the phrases from the page.
        """
        for lang in self.languages:
            LOG.warning('Importing phrases for lang: %s...', lang)
            loaded_xml = _get_wiki_content(lang)

            # One match will be of format [label, class, type, operator, plural]
            matches = self.occurence_pattern.findall(loaded_xml)

            for match in matches:
                yield SpecialPhrase(match[0],
                                    match[1],
                                    self.type_fix_pattern.sub('', match[2]),
                                    match[3])
