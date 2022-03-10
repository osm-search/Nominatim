# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for generic token analysis, mutation part.
"""
import pytest

from icu import Transliterator

import nominatim.tokenizer.token_analysis.generic as module
from nominatim.errors import UsageError

DEFAULT_NORMALIZATION = """ '🜳' > ' ';
                            [[:Nonspacing Mark:] [:Cf:]] >;
                            :: lower ();
                            [[:Punctuation:][:Space:]]+ > ' '
                        """

DEFAULT_TRANSLITERATION = """ ::  Latin ();
                              '🜵' > ' ';
                          """

class TestMutationNoVariants:

    def make_analyser(self, *mutations):
        rules = { 'analyzer': 'generic',
                  'mutations': [ {'pattern': m[0], 'replacements': m[1]}
                                 for m in mutations]
                }
        config = module.configure(rules, DEFAULT_NORMALIZATION)
        trans = Transliterator.createFromRules("test_trans", DEFAULT_TRANSLITERATION)
        norm = Transliterator.createFromRules("test_norm", DEFAULT_NORMALIZATION)

        self.analysis = module.create(norm, trans, config)


    def variants(self, name):
        norm = Transliterator.createFromRules("test_norm", DEFAULT_NORMALIZATION)
        return set(self.analysis.get_variants_ascii(norm.transliterate(name).strip()))


    @pytest.mark.parametrize('pattern', ('(capture)', ['a list']))
    def test_bad_pattern(self, pattern):
        with pytest.raises(UsageError):
            self.make_analyser((pattern, ['b']))


    @pytest.mark.parametrize('replacements', (None, 'a string'))
    def test_bad_replacement(self, replacements):
        with pytest.raises(UsageError):
            self.make_analyser(('a', replacements))


    def test_simple_replacement(self):
        self.make_analyser(('a', ['b']))

        assert self.variants('none') == {'none'}
        assert self.variants('abba') == {'bbbb'}
        assert self.variants('2 aar') == {'2 bbr'}


    def test_multichar_replacement(self):
        self.make_analyser(('1 1', ['1 1 1']))

        assert self.variants('1 1456') == {'1 1 1456'}
        assert self.variants('1 1 1') == {'1 1 1 1'}


    def test_removement_replacement(self):
        self.make_analyser((' ', [' ', '']))

        assert self.variants('A 345') == {'a 345', 'a345'}
        assert self.variants('a g b') == {'a g b', 'ag b', 'a gb', 'agb'}


    def test_regex_pattern(self):
        self.make_analyser(('[^a-z]+', ['XXX', ' ']))

        assert self.variants('a-34n12') == {'aXXXnXXX', 'aXXXn', 'a nXXX', 'a n'}


    def test_multiple_mutations(self):
        self.make_analyser(('ä', ['ä', 'ae']), ('ö', ['ö', 'oe']))

        assert self.variants('Längenöhr') == {'längenöhr', 'laengenöhr',
                                              'längenoehr', 'laengenoehr'}
