# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This file divides Japanese addresses into three categories:
prefecture, municipality, and other.
The division is not strict but simple using these keywords.
"""
from typing import List
import re

from .config import QueryConfig
from .base import QueryProcessingFunc
from ..search.query import Phrase

MATCH_PATTERNS = [
    r'''
                (...??[都都道府県縣])            # [group1] prefecture
                (.+?[市区區町村])              # [group2] municipalities (city/wards/towns/villages)
                (.+)                         # [group3] other words
                ''',
    r'''
                (...??[都都道府県縣])            # [group1] prefecture
                (.+)                         # [group3] other words
                ''',
    r'''
                (.+?[市区區町村])              # [group2] municipalities (city/wards/towns/villages)
                (.+)                         # [group3] other words
                '''
]


class _JapanesePreprocessing:

    def __init__(self, config: QueryConfig) -> None:
        self.config = config

    def split_phrase(self, phrase: Phrase) -> Phrase:
        """
        This function performs a division on the given text using a regular expression.
        """
        for pattern in MATCH_PATTERNS:
            result = re.match(pattern, phrase.text, re.VERBOSE)
            if result is not None:
                return Phrase(phrase.ptype, ':'.join(result.groups()))

        return phrase

    def __call__(self, phrases: List[Phrase]) -> List[Phrase]:
        """Split a Japanese address using japanese_tokenizer.
        """
        return [self.split_phrase(p) for p in phrases]


def create(config: QueryConfig) -> QueryProcessingFunc:
    """ Create a function of japanese preprocessing.
    """
    return _JapanesePreprocessing(config)
