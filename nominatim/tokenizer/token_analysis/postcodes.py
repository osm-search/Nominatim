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
from typing import Any, List

from nominatim.tokenizer.token_analysis.generic_mutation import MutationVariantGenerator
from nominatim.data.place_name import PlaceName

### Configuration section

def configure(*_: Any) -> None:
    """ All behaviour is currently hard-coded.
    """
    return None

### Analysis section

def create(normalizer: Any, transliterator: Any, config: None) -> 'PostcodeTokenAnalysis': # pylint: disable=W0613
    """ Create a new token analysis instance for this module.
    """
    return PostcodeTokenAnalysis(normalizer, transliterator)


class PostcodeTokenAnalysis:
    """ Special normalization and variant generation for postcodes.

        This analyser must not be used with anything but postcodes as
        it follows some special rules: the canonial ID is the form that
        is used for the output. `compute_variants` then needs to ensure that
        the generated variants once more follow the standard normalization
        and transliteration, so that postcodes are correctly recognised by
        the search algorithm.
    """
    def __init__(self, norm: Any, trans: Any) -> None:
        self.norm = norm
        self.trans = trans

        self.mutator = MutationVariantGenerator(' ', (' ', ''))


    def get_canonical_id(self, name: PlaceName) -> str:
        """ Return the standard form of the postcode.
        """
        return name.name.strip().upper()


    def compute_variants(self, norm_name: str) -> List[str]:
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
