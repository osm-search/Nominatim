# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for special postcode analysis and variant generation.
"""
import pytest

from icu import Transliterator

import nominatim.tokenizer.token_analysis.postcodes as module
from nominatim.data.place_name import PlaceName
from nominatim.errors import UsageError

DEFAULT_NORMALIZATION = """ :: NFD ();
                            '🜳' > ' ';
                            [[:Nonspacing Mark:] [:Cf:]] >;
                            :: lower ();
                            [[:Punctuation:][:Space:]]+ > ' ';
                            :: NFC ();
                        """

DEFAULT_TRANSLITERATION = """ ::  Latin ();
                              '🜵' > ' ';
                          """

@pytest.fixture
def analyser():
    rules = { 'analyzer': 'postcodes'}
    config = module.configure(rules, DEFAULT_NORMALIZATION)

    trans = Transliterator.createFromRules("test_trans", DEFAULT_TRANSLITERATION)
    norm = Transliterator.createFromRules("test_norm", DEFAULT_NORMALIZATION)

    return module.create(norm, trans, config)


def get_normalized_variants(proc, name):
    norm = Transliterator.createFromRules("test_norm", DEFAULT_NORMALIZATION)
    return proc.compute_variants(norm.transliterate(name).strip())


@pytest.mark.parametrize('name,norm', [('12', '12'),
                                       ('A 34 ', 'A 34'),
                                       ('34-av', '34-AV')])
def test_get_canonical_id(analyser, name, norm):
    assert analyser.get_canonical_id(PlaceName(name=name, kind='', suffix='')) == norm


@pytest.mark.parametrize('postcode,variants', [('12345', {'12345'}),
                                               ('AB-998', {'ab 998', 'ab998'}),
                                               ('23 FGH D3', {'23 fgh d3', '23fgh d3',
                                                              '23 fghd3', '23fghd3'})])
def test_compute_variants(analyser, postcode, variants):
    out = analyser.compute_variants(postcode)

    assert len(out) == len(set(out))
    assert set(out) == variants
