# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Specialized processor for housenumbers. Analyses common housenumber patterns
and creates variants for them.
"""
from typing import Any, List, cast
import re

from nominatim.data.place_name import PlaceName
from nominatim.tokenizer.token_analysis.generic_mutation import MutationVariantGenerator

RE_NON_DIGIT = re.compile('[^0-9]')
RE_DIGIT_ALPHA = re.compile(r'(\d)\s*([^\d\s␣])')
RE_ALPHA_DIGIT = re.compile(r'([^\s\d␣])\s*(\d)')
RE_NAMED_PART = re.compile(r'[a-z]{4}')

### Configuration section

def configure(*_: Any) -> None:
    """ All behaviour is currently hard-coded.
    """
    return None

### Analysis section

def create(normalizer: Any, transliterator: Any, config: None) -> 'HousenumberTokenAnalysis': # pylint: disable=W0613
    """ Create a new token analysis instance for this module.
    """
    return HousenumberTokenAnalysis(normalizer, transliterator)


class HousenumberTokenAnalysis:
    """ Detects common housenumber patterns and normalizes them.
    """
    def __init__(self, norm: Any, trans: Any) -> None:
        self.norm = norm
        self.trans = trans

        self.mutator = MutationVariantGenerator('␣', (' ', ''))

    def get_canonical_id(self, name: PlaceName) -> str:
        """ Return the normalized form of the housenumber.
        """
        # shortcut for number-only numbers, which make up 90% of the data.
        if RE_NON_DIGIT.search(name.name) is None:
            return name.name

        norm = cast(str, self.trans.transliterate(self.norm.transliterate(name.name)))
        # If there is a significant non-numeric part, use as is.
        if RE_NAMED_PART.search(norm) is None:
            # Otherwise add optional spaces between digits and letters.
            (norm_opt, cnt1) = RE_DIGIT_ALPHA.subn(r'\1␣\2', norm)
            (norm_opt, cnt2) = RE_ALPHA_DIGIT.subn(r'\1␣\2', norm_opt)
            # Avoid creating too many variants per number.
            if cnt1 + cnt2 <= 4:
                return norm_opt

        return norm

    def compute_variants(self, norm_name: str) -> List[str]:
        """ Compute the spelling variants for the given normalized housenumber.

            Generates variants for optional spaces (marked with '␣').
        """
        return list(self.mutator.generate([norm_name]))
