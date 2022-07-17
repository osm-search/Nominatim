# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Container class collecting all components required to transform an OSM name
into a Nominatim token.
"""
from typing import Mapping, Optional, TYPE_CHECKING
from icu import Transliterator

from nominatim.tokenizer.token_analysis.base import Analyser

if TYPE_CHECKING:
    from typing import Any
    from nominatim.tokenizer.icu_rule_loader import TokenAnalyzerRule # pylint: disable=cyclic-import

class ICUTokenAnalysis:
    """ Container class collecting the transliterators and token analysis
        modules for a single NameAnalyser instance.
    """

    def __init__(self, norm_rules: str, trans_rules: str,
                 analysis_rules: Mapping[Optional[str], 'TokenAnalyzerRule']):
        self.normalizer = Transliterator.createFromRules("icu_normalization",
                                                         norm_rules)
        trans_rules += ";[:Space:]+ > ' '"
        self.to_ascii = Transliterator.createFromRules("icu_to_ascii",
                                                       trans_rules)
        self.search = Transliterator.createFromRules("icu_search",
                                                     norm_rules + trans_rules)

        self.analysis = {name: arules.create(self.normalizer, self.to_ascii)
                         for name, arules in analysis_rules.items()}


    def get_analyzer(self, name: Optional[str]) -> Analyser:
        """ Return the given named analyzer. If no analyzer with that
            name exists, return the default analyzer.
        """
        return self.analysis.get(name) or self.analysis[None]
