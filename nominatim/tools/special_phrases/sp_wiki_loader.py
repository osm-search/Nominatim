"""
    Module containing the SPWikiLoader class.
"""
import re
import logging
from collections.abc import Iterator
from nominatim.tools.special_phrases.special_phrase import SpecialPhrase
from nominatim.tools.exec_utils import get_url

LOG = logging.getLogger()
class SPWikiLoader(Iterator):
    """
        Handles loading of special phrases from the wiki.
    """
    def __init__(self, config, languages=None):
        super().__init__()
        self.config = config
        # Compile the regex here to increase performances.
        self.occurence_pattern = re.compile(
            r'\| *([^\|]+) *\|\| *([^\|]+) *\|\| *([^\|]+) *\|\| *([^\|]+) *\|\| *([\-YN])'
        )
        self.languages = self._load_languages() if not languages else list(languages)

    def __next__(self):
        if not self.languages:
            raise StopIteration

        lang = self.languages.pop(0)
        loaded_xml = self._get_wiki_content(lang)
        LOG.warning('Importing phrases for lang: %s...', lang)
        return self.parse_xml(loaded_xml)

    def parse_xml(self, xml):
        """
            Parses XML content and extracts special phrases from it.
            Return a list of SpecialPhrase.
        """
        # One match will be of format [label, class, type, operator, plural]
        matches = self.occurence_pattern.findall(xml)
        returned_phrases = set()
        for match in matches:
            returned_phrases.add(
                SpecialPhrase(match[0], match[1], match[2], match[3])
            )
        return returned_phrases

    def _load_languages(self):
        """
            Get list of all languages from env config file
            or default if there is no languages configured.
            The system will extract special phrases only from all specified languages.
        """
        default_languages = [
            'af', 'ar', 'br', 'ca', 'cs', 'de', 'en', 'es',
            'et', 'eu', 'fa', 'fi', 'fr', 'gl', 'hr', 'hu',
            'ia', 'is', 'it', 'ja', 'mk', 'nl', 'no', 'pl',
            'ps', 'pt', 'ru', 'sk', 'sl', 'sv', 'uk', 'vi']
        return self.config.LANGUAGES.split(',') if self.config.LANGUAGES else default_languages

    @staticmethod
    def _get_wiki_content(lang):
        """
            Request and return the wiki page's content
            corresponding to special phrases for a given lang.
            Requested URL Example :
                https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/EN
        """
        url = 'https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/' \
              + lang.upper()
        return get_url(url)
