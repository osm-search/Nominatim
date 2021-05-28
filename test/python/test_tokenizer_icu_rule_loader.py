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
        """)
        content += "compound_suffixes:\n"
        content += '\n'.join(("    - " + s for s in suffixes)) + '\n'
        content += "abbreviations:\n"
        content += '\n'.join(("    - " + s for s in abbr)) + '\n'
        fpath = tmp_path / ('test_config' + suffix)
        fpath.write_text(dedent(content))
        return fpath

    return _create_config

def test_missing_normalization(tmp_path):
    fpath = tmp_path / ('test_config.yaml')
    fpath.write_text(dedent("""\
        normalizatio:
            - ":: NFD ()"
        """))

    with pytest.raises(UsageError):
        ICURuleLoader(fpath)


def test_get_search_rules(cfgfile):
    fpath = cfgfile(['strasse', 'straße', 'weg'],
                    ['strasse,straße => str',
                     'prospekt => pr'])

    loader = ICURuleLoader(fpath)

    rules = loader.get_search_rules()
    trans = Transliterator.createFromRules("test", rules)

    assert trans.transliterate(" Baumstraße ") == " baum straße "
    assert trans.transliterate(" Baumstrasse ") == " baum strasse "
    assert trans.transliterate(" Baumstr ") == " baum str "
    assert trans.transliterate(" Baumwegstr ") == " baumweg str "
    assert trans.transliterate(" Αθήνα ") == " athēna "
    assert trans.transliterate(" проспект ") == " prospekt "


def test_get_synonym_pairs(cfgfile):
    fpath = cfgfile(['Weg', 'Strasse'],
                    ['Strasse => str,st'])

    loader = ICURuleLoader(fpath)

    repl = loader.get_replacement_pairs()

    assert repl == [(' strasse ', {' strasse ', ' str ', ' st '}),
                    ('strasse ', {' strasse ', ' str ', ' st '}),
                    ('weg ', {' weg '})]

