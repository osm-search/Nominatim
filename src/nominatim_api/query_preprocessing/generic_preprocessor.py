from typing import List, Dict, Any
import re

from .config import QueryConfig
from .base import QueryProcessingFunc
from ..search.query import Phrase


class _GenericPreprocessor:
    """Apply regex replacements to phrases according to configuration."""

    def __init__(self, config: QueryConfig) -> None:
        self.config = config
        self.replacements = []
        self.replace_all = True
        self.ignore_case = False

        # Extract configuration if available
        if hasattr(config, 'REGEX_REPLACE'):
            if 'replacements' in config.REGEX_REPLACE:
                self.replacements = config.REGEX_REPLACE['replacements']
            if 'flags' in config.REGEX_REPLACE:
                flags = config.REGEX_REPLACE['flags']
                if 'replace_all' in flags:
                    self.replace_all = flags['replace_all']
                if 'ignore_case' in flags:
                    self.ignore_case = flags['ignore_case']

    def apply_replacements(self, phrase: Phrase) -> Phrase:
        """Apply all configured regex replacements to a phrase."""
        text = phrase.text

        for replacement in self.replacements:
            pattern = replacement['pattern']
            replace = replacement['replace']

            # Apply flags
            flags = 0
            if self.ignore_case:
                flags |= re.IGNORECASE

            # Apply replacement
            if self.replace_all:
                text = re.sub(pattern, replace, text, flags=flags)
            else:
                text = re.sub(pattern, replace, text, count=1, flags=flags)

        # Create a new phrase with the replaced text
        return Phrase(phrase.ptype, text)

    def __call__(self, phrases: List[Phrase]) -> List[Phrase]:
        """Process phrases with configured regex replacements.
        Empty phrases after replacement are filtered out.
        """
        result = []
        for phrase in phrases:
            processed = self.apply_replacements(phrase)
            if processed.text:  # Only keep non-empty phrases
                result.append(processed)
        return result


def create(config: QueryConfig) -> QueryProcessingFunc:
    """Create a function for generic regex-based preprocessing."""
    return _GenericPreprocessor(config)
