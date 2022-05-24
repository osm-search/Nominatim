# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Specialized processor for postcodes. Supports a 'lookup' variant of the
token, which produces variants with optional spaces.
"""

from nominatim.tokenizer.token_analysis.generic_mutation import MutationVariantGenerator

### Configuration section

def configure(rules, normalization_rules): # pylint: disable=W0613
    """ All behaviour is currently hard-coded.
    """
    return None

### Analysis section

def create(normalizer, transliterator, config): # pylint: disable=W0613
    """ Create a new token analysis instance for this module.
    """
    return PostcodeTokenAnalysis(normalizer, transliterator)

class PostcodeTokenAnalysis:
    """ Detects common housenumber patterns and normalizes them.
    """
    def __init__(self, norm, trans):
        self.norm = norm
        self.trans = trans

        self.mutator = MutationVariantGenerator(' ', (' ', ''))


    def normalize(self, name):
        """ Return the standard form of the postcode.
        """
        return name.strip().upper()


    def get_variants_ascii(self, norm_name):
        """ Compute the spelling variants for the given normalized postcode.

            The official form creates one variant. If a 'lookup version' is
            given, then it will create variants with optional spaces.
        """
        # Postcodes follow their own transliteration rules.
        # Make sure at this point, that the terms are normalized in a way
        # that they are searchable with the standard transliteration rules.
        return [self.trans.transliterate(term) for term in
                self.mutator.generate([self.norm.transliterate(norm_name)])]
