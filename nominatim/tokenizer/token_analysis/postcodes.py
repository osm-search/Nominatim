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
    """ Special normalization and variant generation for postcodes.

        This analyser must not be used with anything but postcodes as
        it follows some special rules: `normalize` doesn't necessarily
        need to return a standard form as per normalization rules. It
        needs to return the canonical form of the postcode that is also
        used for output. `get_variants_ascii` then needs to ensure that
        the generated variants once more follow the standard normalization
        and transliteration, so that postcodes are correctly recognised by
        the search algorithm.
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

            Takes the canonical form of the postcode, normalizes it using the
            standard rules and then creates variants of the result where
            all spaces are optional.
        """
        # Postcodes follow their own transliteration rules.
        # Make sure at this point, that the terms are normalized in a way
        # that they are searchable with the standard transliteration rules.
        return [self.trans.transliterate(term) for term in
                self.mutator.generate([self.norm.transliterate(norm_name)]) if term]
