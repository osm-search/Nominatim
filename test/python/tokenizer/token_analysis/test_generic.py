# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for import name normalisation and variant generation.
"""
import pytest

from icu import Transliterator

import nominatim.tokenizer.token_analysis.generic as module
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

def make_analyser(*variants, variant_only=False):
    rules = { 'analyzer': 'generic', 'variants': [{'words': variants}]}
    if variant_only:
        rules['mode'] = 'variant-only'
    config = module.configure(rules, DEFAULT_NORMALIZATION)
    trans = Transliterator.createFromRules("test_trans", DEFAULT_TRANSLITERATION)
    norm = Transliterator.createFromRules("test_norm", DEFAULT_NORMALIZATION)

    return module.create(norm, trans, config)


def get_normalized_variants(proc, name):
    norm = Transliterator.createFromRules("test_norm", DEFAULT_NORMALIZATION)
    return proc.get_variants_ascii(norm.transliterate(name).strip())


def test_no_variants():
    rules = { 'analyzer': 'generic' }
    config = module.configure(rules, DEFAULT_NORMALIZATION)
    trans = Transliterator.createFromRules("test_trans", DEFAULT_TRANSLITERATION)
    norm = Transliterator.createFromRules("test_norm", DEFAULT_NORMALIZATION)

    proc = module.create(norm, trans, config)

    assert get_normalized_variants(proc, '大德!') == ['dà dé']


def test_variants_empty():
    proc = make_analyser('saint -> 🜵', 'street -> st')

    assert get_normalized_variants(proc, '🜵') == []
    assert get_normalized_variants(proc, '🜳') == []
    assert get_normalized_variants(proc, 'saint') == ['saint']


VARIANT_TESTS = [
(('~strasse,~straße -> str', '~weg => weg'), "hallo", {'hallo'}),
(('weg => wg',), "holzweg", {'holzweg'}),
(('weg -> wg',), "holzweg", {'holzweg'}),
(('~weg => weg',), "holzweg", {'holz weg', 'holzweg'}),
(('~weg -> weg',), "holzweg",  {'holz weg', 'holzweg'}),
(('~weg => w',), "holzweg", {'holz w', 'holzw'}),
(('~weg -> w',), "holzweg",  {'holz weg', 'holzweg', 'holz w', 'holzw'}),
(('~weg => weg',), "Meier Weg", {'meier weg', 'meierweg'}),
(('~weg -> weg',), "Meier Weg", {'meier weg', 'meierweg'}),
(('~weg => w',), "Meier Weg", {'meier w', 'meierw'}),
(('~weg -> w',), "Meier Weg", {'meier weg', 'meierweg', 'meier w', 'meierw'}),
(('weg => wg',), "Meier Weg", {'meier wg'}),
(('weg -> wg',), "Meier Weg", {'meier weg', 'meier wg'}),
(('~strasse,~straße -> str', '~weg => weg'), "Bauwegstraße",
     {'bauweg straße', 'bauweg str', 'bauwegstraße', 'bauwegstr'}),
(('am => a', 'bach => b'), "am bach", {'a b'}),
(('am => a', '~bach => b'), "am bach", {'a b'}),
(('am -> a', '~bach -> b'), "am bach", {'am bach', 'a bach', 'am b', 'a b'}),
(('am -> a', '~bach -> b'), "ambach", {'ambach', 'am bach', 'amb', 'am b'}),
(('saint -> s,st', 'street -> st'), "Saint Johns Street",
     {'saint johns street', 's johns street', 'st johns street',
      'saint johns st', 's johns st', 'st johns st'}),
(('river$ -> r',), "River Bend Road", {'river bend road'}),
(('river$ -> r',), "Bent River", {'bent river', 'bent r'}),
(('^north => n',), "North 2nd Street", {'n 2nd street'}),
(('^north => n',), "Airport North", {'airport north'}),
(('am -> a',), "am am am am am am am am", {'am am am am am am am am'}),
(('am => a',), "am am am am am am am am", {'a a a a a a a a'})
]

@pytest.mark.parametrize("rules,name,variants", VARIANT_TESTS)
def test_variants(rules, name, variants):
    proc = make_analyser(*rules)

    result = get_normalized_variants(proc, name)

    assert len(result) == len(set(result))
    assert set(get_normalized_variants(proc, name)) == variants


VARIANT_ONLY_TESTS = [
(('weg => wg',), "hallo", set()),
(('weg => wg',), "Meier Weg", {'meier wg'}),
(('weg -> wg',), "Meier Weg", {'meier wg'}),
]

@pytest.mark.parametrize("rules,name,variants", VARIANT_ONLY_TESTS)
def test_variants_only(rules, name, variants):
    proc = make_analyser(*rules, variant_only=True)

    result = get_normalized_variants(proc, name)

    assert len(result) == len(set(result))
    assert set(get_normalized_variants(proc, name)) == variants


class TestGetReplacements:

    @staticmethod
    def configure_rules(*variants):
        rules = { 'analyzer': 'generic', 'variants': [{'words': variants}]}
        return module.configure(rules, DEFAULT_NORMALIZATION)


    def get_replacements(self, *variants):
        config = self.configure_rules(*variants)

        return sorted((k, sorted(v)) for k,v in config['replacements'])


    @pytest.mark.parametrize("variant", ['foo > bar', 'foo -> bar -> bar',
                                         '~foo~ -> bar', 'fo~ o -> bar'])
    def test_invalid_variant_description(self, variant):
        with pytest.raises(UsageError):
            self.configure_rules(variant)


    @pytest.mark.parametrize("rule", ["!!! -> bar", "bar => !!!"])
    def test_ignore_unnormalizable_terms(self, rule):
        repl = self.get_replacements(rule)

        assert repl == []


    def test_add_full(self):
        repl = self.get_replacements("foo -> bar")

        assert repl == [(' foo ', [' bar', ' foo'])]


    def test_replace_full(self):
        repl = self.get_replacements("foo => bar")

        assert repl == [(' foo ', [' bar'])]


    def test_add_suffix_no_decompose(self):
        repl = self.get_replacements("~berg |-> bg")

        assert repl == [(' berg ', [' berg', ' bg']),
                        ('berg ', ['berg', 'bg'])]


    def test_replace_suffix_no_decompose(self):
        repl = self.get_replacements("~berg |=> bg")

        assert repl == [(' berg ', [' bg']),('berg ', ['bg'])]


    def test_add_suffix_decompose(self):
        repl = self.get_replacements("~berg -> bg")

        assert repl == [(' berg ', [' berg', ' bg', 'berg', 'bg']),
                        ('berg ', [' berg', ' bg', 'berg', 'bg'])]


    def test_replace_suffix_decompose(self):
        repl = self.get_replacements("~berg => bg")

        assert repl == [(' berg ', [' bg', 'bg']),
                        ('berg ', [' bg', 'bg'])]


    def test_add_prefix_no_compose(self):
        repl = self.get_replacements("hinter~ |-> hnt")

        assert repl == [(' hinter', [' hinter', ' hnt']),
                        (' hinter ', [' hinter', ' hnt'])]


    def test_replace_prefix_no_compose(self):
        repl = self.get_replacements("hinter~ |=> hnt")

        assert repl ==  [(' hinter', [' hnt']), (' hinter ', [' hnt'])]


    def test_add_prefix_compose(self):
        repl = self.get_replacements("hinter~-> h")

        assert repl == [(' hinter', [' h', ' h ', ' hinter', ' hinter ']),
                        (' hinter ', [' h', ' h', ' hinter', ' hinter'])]


    def test_replace_prefix_compose(self):
        repl = self.get_replacements("hinter~=> h")

        assert repl == [(' hinter', [' h', ' h ']),
                        (' hinter ', [' h', ' h'])]


    def test_add_beginning_only(self):
        repl = self.get_replacements("^Premier -> Pr")

        assert repl == [('^ premier ', ['^ pr', '^ premier'])]


    def test_replace_beginning_only(self):
        repl = self.get_replacements("^Premier => Pr")

        assert repl == [('^ premier ', ['^ pr'])]


    def test_add_final_only(self):
        repl = self.get_replacements("road$ -> rd")

        assert repl == [(' road ^', [' rd ^', ' road ^'])]


    def test_replace_final_only(self):
        repl = self.get_replacements("road$ => rd")

        assert repl == [(' road ^', [' rd ^'])]


    def test_decompose_only(self):
        repl = self.get_replacements("~foo -> foo")

        assert repl == [(' foo ', [' foo', 'foo']),
                        ('foo ', [' foo', 'foo'])]


    def test_add_suffix_decompose_end_only(self):
        repl = self.get_replacements("~berg |-> bg", "~berg$ -> bg")

        assert repl == [(' berg ', [' berg', ' bg']),
                        (' berg ^', [' berg ^', ' bg ^', 'berg ^', 'bg ^']),
                        ('berg ', ['berg', 'bg']),
                        ('berg ^', [' berg ^', ' bg ^', 'berg ^', 'bg ^'])]


    def test_replace_suffix_decompose_end_only(self):
        repl = self.get_replacements("~berg |=> bg", "~berg$ => bg")

        assert repl == [(' berg ', [' bg']),
                        (' berg ^', [' bg ^', 'bg ^']),
                        ('berg ', ['bg']),
                        ('berg ^', [' bg ^', 'bg ^'])]


    @pytest.mark.parametrize('rule', ["~berg,~burg -> bg",
                                      "~berg, ~burg -> bg",
                                      "~berg,,~burg -> bg"])
    def test_add_multiple_suffix(self, rule):
        repl = self.get_replacements(rule)

        assert repl == [(' berg ', [' berg', ' bg', 'berg', 'bg']),
                        (' burg ', [' bg', ' burg', 'bg', 'burg']),
                        ('berg ', [' berg', ' bg', 'berg', 'bg']),
                        ('burg ', [' bg', ' burg', 'bg', 'burg'])]
