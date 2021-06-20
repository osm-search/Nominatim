"""
Tests for converting a config file to ICU rules.
"""
import pytest
from textwrap import dedent

from nominatim.tokenizer.icu_rule_loader import ICURuleLoader
from nominatim.errors import UsageError

from icu import Transliterator

@pytest.fixture
def cfgfile(tmp_path, suffix='.yaml'):
    def _create_config(suffixes, abbr):
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
        """)
        content += "compound_suffixes:\n"
        content += '\n'.join(("    - " + s for s in suffixes)) + '\n'
        content += "abbreviations:\n"
        content += '\n'.join(("    - " + s for s in abbr)) + '\n'
        fpath = tmp_path / ('test_config' + suffix)
        fpath.write_text(dedent(content))
        return fpath

    return _create_config


def test_empty_rule_file(tmp_path):
    fpath = tmp_path / ('test_config.yaml')
    fpath.write_text(dedent("""\
        normalization:
        transliteration:
        compound_suffixes:
        abbreviations:
        """))

    rules = ICURuleLoader(fpath)
    assert rules.get_search_rules() == ''
    assert rules.get_normalization_rules() == ''
    assert rules.get_transliteration_rules() == ''
    assert rules.get_replacement_pairs() == []

CONFIG_SECTIONS = ('normalization', 'transliteration',
                   'compound_suffixes', 'abbreviations')

@pytest.mark.parametrize("section", CONFIG_SECTIONS)
def test_missing_normalization(tmp_path, section):
    fpath = tmp_path / ('test_config.yaml')
    with fpath.open('w') as fd:
        for name in CONFIG_SECTIONS:
            if name != section:
                fd.write(name + ':\n')

    with pytest.raises(UsageError):
        ICURuleLoader(fpath)

@pytest.mark.parametrize("abbr", ["simple",
                                  "double => arrow => bad",
                                  "bad = > arrow"])
def test_bad_abbreviation_syntax(tmp_path, abbr):
    fpath = tmp_path / ('test_config.yaml')
    fpath.write_text(dedent("""\
        normalization:
        transliteration:
        compound_suffixes:
        abbreviations:
         - {}
        """.format(abbr)))

    with pytest.raises(UsageError):
        rules = ICURuleLoader(fpath)


def test_get_search_rules(cfgfile):
    fpath = cfgfile(['strasse', 'straße', 'weg'],
                    ['strasse,straße => str',
                     'prospekt => pr'])

    loader = ICURuleLoader(fpath)

    rules = loader.get_search_rules()
    trans = Transliterator.createFromRules("test", rules)

    assert trans.transliterate(" Baum straße ") == " baum straße "
    assert trans.transliterate(" Baumstraße ") == " baumstraße "
    assert trans.transliterate(" Baumstrasse ") == " baumstrasse "
    assert trans.transliterate(" Baumstr ") == " baumstr "
    assert trans.transliterate(" Baumwegstr ") == " baumwegstr "
    assert trans.transliterate(" Αθήνα ") == " athēna "
    assert trans.transliterate(" проспект ") == " prospekt "


def test_get_normalization_rules(cfgfile):
    fpath = cfgfile(['strasse', 'straße', 'weg'],
                    ['strasse,straße => str'])

    loader = ICURuleLoader(fpath)
    rules = loader.get_normalization_rules()
    trans = Transliterator.createFromRules("test", rules)

    assert trans.transliterate(" проспект-Prospekt ") == " проспект prospekt "


def test_get_transliteration_rules(cfgfile):
    fpath = cfgfile(['strasse', 'straße', 'weg'],
                    ['strasse,straße => str'])

    loader = ICURuleLoader(fpath)
    rules = loader.get_transliteration_rules()
    trans = Transliterator.createFromRules("test", rules)

    assert trans.transliterate(" проспект-Prospekt ") == " prospekt Prospekt "


def test_transliteration_rules_from_file(tmp_path):
    cfgpath = tmp_path / ('test_config.yaml')
    cfgpath.write_text(dedent("""\
        normalization:
        transliteration:
            - "'ax' > 'b'"
            - !include transliteration.yaml
        compound_suffixes:
        abbreviations:
        """))
    transpath = tmp_path / ('transliteration.yaml')
    transpath.write_text('- "x > y"')

    loader = ICURuleLoader(cfgpath)
    rules = loader.get_transliteration_rules()
    trans = Transliterator.createFromRules("test", rules)

    assert trans.transliterate(" axxt ") == " byt "


def test_get_replacement_pairs_multi_to(cfgfile):
    fpath = cfgfile(['Pfad', 'Strasse'],
                    ['Strasse => str,st'])

    repl = ICURuleLoader(fpath).get_replacement_pairs()

    assert [(a, sorted(b)) for a, b in repl] == \
             [(' strasse ', [' st ', ' str ', ' strasse ', 'st ', 'str ', 'strasse ']),
              ('strasse ', [' st ', ' str ', ' strasse ', 'st ', 'str ', 'strasse ']),
              (' pfad ', [' pfad ', 'pfad ']),
              ('pfad ', [' pfad ', 'pfad '])]


def test_get_replacement_pairs_multi_from(cfgfile):
    fpath = cfgfile([], ['saint,Sainte => st'])

    repl = ICURuleLoader(fpath).get_replacement_pairs()

    assert [(a, sorted(b)) for a, b in repl] == \
             [(' sainte ', [' sainte ', ' st ']),
              (' saint ', [' saint ', ' st '])]


def test_get_replacement_pairs_cross_abbreviations(cfgfile):
    fpath = cfgfile([], ['saint,Sainte => st',
                         'sainte => ste'])

    repl = ICURuleLoader(fpath).get_replacement_pairs()

    assert [(a, sorted(b)) for a, b in repl] == \
             [(' sainte ', [' sainte ', ' st ', ' ste ']),
              (' saint ', [' saint ', ' st '])]


@pytest.mark.parametrize("abbr", ["missing to =>",
                                  "  => missing from",
                                  "=>"])
def test_bad_abbreviation_syntax(tmp_path, abbr):
    fpath = tmp_path / ('test_config.yaml')
    fpath.write_text(dedent("""\
        normalization:
        transliteration:
        compound_suffixes:
        abbreviations:
         - {}
        """.format(abbr)))

    repl = ICURuleLoader(fpath).get_replacement_pairs()

    assert repl == []
