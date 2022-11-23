# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for sanitizer that clean up TIGER tags.
"""
import pytest

from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.data.place_info import PlaceInfo

class TestCleanTigerTags:

    @pytest.fixture(autouse=True)
    def setup_country(self, def_config):
        self.config = def_config


    def run_sanitizer_on(self, addr):
        place = PlaceInfo({'address': addr})
        _, outaddr = PlaceSanitizer([{'step': 'clean-tiger-tags'}], self.config).process_names(place)

        return sorted([(p.name, p.kind, p.suffix) for p in outaddr])

    @pytest.mark.parametrize('inname,outname', [('Hamilton, AL', 'Hamilton'),
                                                ('Little, Borough, CA', 'Little, Borough')])
    def test_well_formatted(self, inname, outname):
        assert self.run_sanitizer_on({'tiger:county': inname})\
            == [(outname, 'county', 'tiger')]


    @pytest.mark.parametrize('name', ('Hamilton', 'Big, Road', ''))
    def test_badly_formatted(self, name):
        assert self.run_sanitizer_on({'tiger:county': name})\
            == [(name, 'county', 'tiger')]


    def test_unmatched(self):
        assert self.run_sanitizer_on({'tiger:country': 'US'})\
            == [('US', 'tiger', 'country')]
