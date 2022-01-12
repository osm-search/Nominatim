# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for converting a config file to ICU rules.
"""
from textwrap import dedent

import pytest
import yaml

from nominatim.tokenizer.icu_rule_loader import ICURuleLoader
from nominatim.errors import UsageError

from icu import Transliterator

CONFIG_SECTIONS = ('normalization', 'transliteration', 'token-analysis')

class TestIcuRuleLoader:

    @pytest.fixture(autouse=True)
    def init_env(self, project_env):
        self.project_env = project_env


    def write_config(self, content):
        (self.project_env.project_dir / 'icu_tokenizer.yaml').write_text(dedent(content))


    def config_rules(self, *variants):
        content = dedent("""\
        normalization:
            - ":: NFD ()"
            - "[[:Nonspacing Mark:] [:Cf:]] >"
            - ":: lower ()"
            - "[[:Punctuation:][:Space:]]+ > ' '"
            - ":: NFC ()"
        transliteration:
            - "::  Latin ()"
            - "[[:Punctuation:][:Space:]]+ > ' '"
        token-analysis:
            - analyzer: generic
              variants:
                  - words:
        """)
        content += '\n'.join(("             - " + s for s in variants)) + '\n'
        self.write_config(content)


    def get_replacements(self, *variants):
        self.config_rules(*variants)
        loader = ICURuleLoader(self.project_env)
        rules = loader.analysis[None].config['replacements']

        return sorted((k, sorted(v)) for k,v in rules)


    def test_empty_rule_set(self):
        self.write_config("""\
            normalization:
            transliteration:
            token-analysis:
              - analyzer: generic
                variants:
            """)

        rules = ICURuleLoader(self.project_env)
        assert rules.get_search_rules() == ''
        assert rules.get_normalization_rules() == ''
        assert rules.get_transliteration_rules() == ''


    @pytest.mark.parametrize("section", CONFIG_SECTIONS)
    def test_missing_section(self, section):
        rule_cfg = { s: [] for s in CONFIG_SECTIONS if s != section}
        self.write_config(yaml.dump(rule_cfg))

        with pytest.raises(UsageError):
            ICURuleLoader(self.project_env)


    def test_get_search_rules(self):
        self.config_rules()
        loader = ICURuleLoader(self.project_env)

        rules = loader.get_search_rules()
        trans = Transliterator.createFromRules("test", rules)

        assert trans.transliterate(" Baum straße ") == " baum straße "
        assert trans.transliterate(" Baumstraße ") == " baumstraße "
        assert trans.transliterate(" Baumstrasse ") == " baumstrasse "
        assert trans.transliterate(" Baumstr ") == " baumstr "
        assert trans.transliterate(" Baumwegstr ") == " baumwegstr "
        assert trans.transliterate(" Αθήνα ") == " athēna "
        assert trans.transliterate(" проспект ") == " prospekt "


    def test_get_normalization_rules(self):
        self.config_rules()
        loader = ICURuleLoader(self.project_env)
        rules = loader.get_normalization_rules()
        trans = Transliterator.createFromRules("test", rules)

        assert trans.transliterate(" проспект-Prospekt ") == " проспект prospekt "


    def test_get_transliteration_rules(self):
        self.config_rules()
        loader = ICURuleLoader(self.project_env)
        rules = loader.get_transliteration_rules()
        trans = Transliterator.createFromRules("test", rules)

        assert trans.transliterate(" проспект-Prospekt ") == " prospekt Prospekt "


    def test_transliteration_rules_from_file(self):
        self.write_config("""\
            normalization:
            transliteration:
                - "'ax' > 'b'"
                - !include transliteration.yaml
            token-analysis:
                - analyzer: generic
                  variants:
            """)
        transpath = self.project_env.project_dir / ('transliteration.yaml')
        transpath.write_text('- "x > y"')

        loader = ICURuleLoader(self.project_env)
        rules = loader.get_transliteration_rules()
        trans = Transliterator.createFromRules("test", rules)

        assert trans.transliterate(" axxt ") == " byt "


    def test_search_rules(self):
        self.config_rules('~street => s,st', 'master => mstr')
        proc = ICURuleLoader(self.project_env).make_token_analysis()

        assert proc.search.transliterate('Master Street').strip() == 'master street'
        assert proc.search.transliterate('Earnes St').strip() == 'earnes st'
        assert proc.search.transliterate('Nostreet').strip() == 'nostreet'


    @pytest.mark.parametrize("variant", ['foo > bar', 'foo -> bar -> bar',
                                         '~foo~ -> bar', 'fo~ o -> bar'])
    def test_invalid_variant_description(self, variant):
        self.config_rules(variant)
        with pytest.raises(UsageError):
            ICURuleLoader(self.project_env)

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


    def test_add_multiple_suffix(self):
        repl = self.get_replacements("~berg,~burg -> bg")

        assert repl == [(' berg ', [' berg', ' bg', 'berg', 'bg']),
                        (' burg ', [' bg', ' burg', 'bg', 'burg']),
                        ('berg ', [' berg', ' bg', 'berg', 'bg']),
                        ('burg ', [' bg', ' burg', 'bg', 'burg'])]
