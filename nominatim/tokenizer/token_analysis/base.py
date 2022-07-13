# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Common data types and protocols for analysers.
"""
from typing import TypeVar, Mapping, List, Any

from typing_extensions import Protocol


T_config = TypeVar('T_config') # pylint: disable=invalid-name

class Analyser(Protocol):
    """ Instance of the token analyser.
    """

    def normalize(self, name: str) -> str:
        """ Return the normalized form of the name. This is the standard form
            from which possible variants for the name can be derived.
        """

    def get_variants_ascii(self, norm_name: str) -> List[str]:
        """ Compute the spelling variants for the given normalized name
            and transliterate the result.
        """

class AnalysisModule(Protocol[T_config]):
    """ Protocol for analysis modules.
    """

    def configure(self, rules: Mapping[str, Any], normalization_rules: str) -> T_config:
        """ Prepare the configuration of the analysis module.
            This function should prepare all data that can be shared
            between instances of this analyser.
        """

    def create(self, normalizer: Any, transliterator: Any, config: T_config) -> Analyser:
        """ Create a new instance of the analyser.
            A separate instance of the analyser is created for each thread
            when used in multi-threading context.
        """
