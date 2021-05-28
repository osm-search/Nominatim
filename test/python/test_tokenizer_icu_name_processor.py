"""
Tests for import name normalisation and variant generation.
"""
from textwrap import dedent

import pytest

from nominatim.tokenizer.icu_rule_loader import ICURuleLoader
from nominatim.tokenizer.icu_name_processor import ICUNameProcessor, ICUNameProcessorRules

from nominatim.errors import UsageError

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


def test_simple_variants(cfgfile):
    fpath = cfgfile(['strasse', 'straße', 'weg'],
                    ['strasse,straße => str',
                     'prospekt => pr'])

    rules = ICUNameProcessorRules(loader=ICURuleLoader(fpath))
    proc = ICUNameProcessor(rules)

    assert set(proc.get_normalized_variants("Bauwegstraße")) \
            == {'bauweg straße', 'bauweg str'}
    assert proc.get_normalized_variants("Bauwegstr") == ['bauweg str']
    assert proc.get_normalized_variants("holzweg") == ['holz weg']
    assert proc.get_normalized_variants("hallo") == ['hallo']


def test_multiple_replacements(cfgfile):
    fpath = cfgfile([], ['saint => s,st', 'street => st'])

    rules = ICUNameProcessorRules(loader=ICURuleLoader(fpath))
    proc = ICUNameProcessor(rules)

    assert set(proc.get_normalized_variants("Saint Johns Street")) == \
            {'saint johns street', 's johns street', 'st johns street',
             'saint johns st', 's johns st', 'st johns st'}
