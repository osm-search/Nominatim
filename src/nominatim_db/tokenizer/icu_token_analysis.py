# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Container class collecting all components required to transform an OSM name
into a Nominatim token.
"""
from typing import Mapping, Optional, TYPE_CHECKING
from icu import Transliterator

from .token_analysis.base import Analyzer

if TYPE_CHECKING:
    from typing import Any  # noqa
    from .icu_rule_loader import TokenAnalyzerRule


class ICUTokenAnalysis:
    """ Container class collecting the transliterators and token analysis
        modules for a single Analyser instance.
    """

    def __init__(self, norm_rules: str, trans_rules: str,
                 analysis_rules: Mapping[Optional[str], 'TokenAnalyzerRule']):
        # additional break signs are not relevant during name analysis
        norm_rules += ";[[:Space:][-:]]+ > ' ';"
        self.normalizer = Transliterator.createFromRules("icu_normalization",
                                                         norm_rules)
        trans_rules += ";[:Space:]+ > ' '"
        self.to_ascii = Transliterator.createFromRules("icu_to_ascii",
                                                       trans_rules)
        self.search = Transliterator.createFromRules("icu_search",
                                                     norm_rules + trans_rules)

        self.analysis = {name: arules.create(self.normalizer, self.to_ascii)
                         for name, arules in analysis_rules.items()}

    def get_analyzer(self, name: Optional[str]) -> Analyzer:
        """ Return the given named analyzer. If no analyzer with that
            name exists, return the default analyzer.
        """
        return self.analysis.get(name) or self.analysis[None]
