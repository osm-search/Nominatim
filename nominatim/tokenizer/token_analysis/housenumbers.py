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
import re

from nominatim.tokenizer.token_analysis.generic_mutation import MutationVariantGenerator

RE_NON_DIGIT = re.compile('[^0-9]')
RE_DIGIT_ALPHA = re.compile(r'(\d)\s*([^\d\s␣])')
RE_ALPHA_DIGIT = re.compile(r'([^\s\d␣])\s*(\d)')

### Configuration section

def configure(rules, normalization_rules):
    """ All behaviour is currently hard-coded.
    """
    return None

### Analysis section

def create(normalizer, transliterator, config):
    """ Create a new token analysis instance for this module.
    """
    return HousenumberTokenAnalysis(normalizer, transliterator)


class HousenumberTokenAnalysis:
    """ Detects common housenumber patterns and normalizes them.
    """
    def __init__(self, norm, trans):
        self.norm = norm
        self.trans = trans

        self.mutator = MutationVariantGenerator('␣', (' ', ''))

    def normalize(self, name):
        """ Return the normalized form of the housenumber.
        """
        # shortcut for number-only numbers, which make up 90% of the data.
        if RE_NON_DIGIT.search(name) is None:
            return name

        norm = self.trans.transliterate(self.norm.transliterate(name))
        norm = RE_DIGIT_ALPHA.sub(r'\1␣\2', norm)
        norm = RE_ALPHA_DIGIT.sub(r'\1␣\2', norm)

        return norm

    def get_variants_ascii(self, norm_name):
        """ Compute the spelling variants for the given normalized housenumber.

            Generates variants for optional spaces (marked with '␣').
        """
        return list(self.mutator.generate([norm_name]))
