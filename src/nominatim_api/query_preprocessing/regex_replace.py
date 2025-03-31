# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This preprocessor replaces values in a given input based on pre-defined regex rules.

Arguments:
    pattern: Regex pattern to be applied on the input
    replace: The string that it is to be replaced with
"""
from typing import List
import re

from .config import QueryConfig
from .base import QueryProcessingFunc
from ..search.query import Phrase


class _GenericPreprocessing:
    """Perform replacements to input phrases using custom regex patterns."""

    def __init__(self, config: QueryConfig) -> None:
        """Initialise the _GenericPreprocessing class with patterns from the ICU config file."""
        self.config = config

        match_patterns = self.config.get('replacements', 'Key not found')
        self.compiled_patterns = [
            (re.compile(item['pattern']), item['replace']) for item in match_patterns
            ]

    def split_phrase(self, phrase: Phrase) -> Phrase:
        """This function performs replacements on the given text using regex patterns."""
        for item in self.compiled_patterns:
            phrase.text = item[0].sub(item[1], phrase.text)

        return phrase

    def __call__(self, phrases: List[Phrase]) -> List[Phrase]:
        """
        Return the final Phrase list.
        Returns an empty list if there is nothing left after split_phrase.
        """
        result = [p for p in map(self.split_phrase, phrases) if p.text.strip()]
        return result


def create(config: QueryConfig) -> QueryProcessingFunc:
    """ Create a function for generic preprocessing."""
    return _GenericPreprocessing(config)
