# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Common data types and protocols for analysers.
"""
from typing import Mapping, List, Any

from nominatim.typing import Protocol
from nominatim.data.place_name import PlaceName

class Analyzer(Protocol):
    """ The `create()` function of an analysis module needs to return an
        object that implements the following functions.
    """

    def get_canonical_id(self, name: PlaceName) -> str:
        """ Return the canonical form of the given name. The canonical ID must
            be unique (the same ID must always yield the same variants) and
            must be a form from which the variants can be derived.

            Arguments:
                name: Extended place name description as prepared by
                      the sanitizers.

            Returns:
                ID string with a canonical form of the name. The string may
                be empty, when the analyzer cannot analyze the name at all,
                for example because the character set in use does not match.
        """

    def compute_variants(self, canonical_id: str) -> List[str]:
        """ Compute the transliterated spelling variants for the given
            canonical ID.

            Arguments:
                canonical_id: ID string previously computed with
                              `get_canonical_id()`.

            Returns:
                A list of possible spelling variants. All strings must have
                been transformed with the global normalizer and
                transliterator ICU rules. Otherwise they cannot be matched
                against the query later.
                The list may be empty, when there are no useful
                spelling variants. This may happen, when an analyzer only
                produces extra variants to the canonical spelling.
        """


class AnalysisModule(Protocol):
    """ Protocol for analysis modules.
    """

    def configure(self, rules: Mapping[str, Any],
                  normalizer: Any, transliterator: Any) -> Any:
        """ Prepare the configuration of the analysis module.
            This function should prepare all data that can be shared
            between instances of this analyser.

            Arguments:
                rules: A dictionary with the additional configuration options
                       as specified in the tokenizer configuration.
                normalizer: an ICU Transliterator with the compiled normalization
                            rules.
                transliterator: an ICU transliterator with the compiled
                                transliteration rules.

            Returns:
                A data object with the configuration that was set up. May be
                used freely by the analysis module as needed.
        """

    def create(self, normalizer: Any, transliterator: Any, config: Any) -> Analyzer:
        """ Create a new instance of the analyser.
            A separate instance of the analyser is created for each thread
            when used in multi-threading context.

            Arguments:
                normalizer: an ICU Transliterator with the compiled normalization
                            rules.
                transliterator: an ICU tranliterator with the compiled
                                transliteration rules.
                config: The object that was returned by the call to configure().

            Returns:
                A new analyzer instance. This must be an object that implements
                the Analyzer protocol.
        """
