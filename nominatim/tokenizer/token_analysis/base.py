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

class Analyzer(Protocol):
    """ The `create()` function of an analysis module needs to return an
        object that implements the following functions.
    """

    def normalize(self, name: str) -> str:
        """ Return the normalized form of the name. This is the standard form
            from which possible variants for the name can be derived.
        """

    def get_variants_ascii(self, norm_name: str) -> List[str]:
        """ Compute the spelling variants for the given normalized name
            and transliterate the result.
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
                transliterator: an ICU tranliterator with the compiled
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
