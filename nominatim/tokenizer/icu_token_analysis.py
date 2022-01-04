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

from icu import Transliterator

class ICUTokenAnalysis:
    """ Container class collecting the transliterators and token analysis
        modules for a single NameAnalyser instance.
    """

    def __init__(self, norm_rules, trans_rules, analysis_rules):
        self.normalizer = Transliterator.createFromRules("icu_normalization",
                                                         norm_rules)
        trans_rules += ";[:Space:]+ > ' '"
        self.to_ascii = Transliterator.createFromRules("icu_to_ascii",
                                                       trans_rules)
        self.search = Transliterator.createFromRules("icu_search",
                                                     norm_rules + trans_rules)

        self.analysis = {name: arules.create(self.to_ascii, arules.config)
                         for name, arules in analysis_rules.items()}
