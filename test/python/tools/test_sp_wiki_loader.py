# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
    Tests for methods of the SPWikiLoader class.
"""
import pytest
from nominatim.tools.special_phrases.sp_wiki_loader import SPWikiLoader

@pytest.fixture
def xml_wiki_content(src_dir):
    """
        return the content of the static xml test file.
    """
    xml_test_content = src_dir / 'test' / 'testdata' / 'special_phrases_test_content.txt'
    return xml_test_content.read_text()


@pytest.fixture
def sp_wiki_loader(monkeypatch, def_config, xml_wiki_content):
    """
        Return an instance of SPWikiLoader.
    """
    monkeypatch.setenv('NOMINATIM_LANGUAGES', 'en')
    loader = SPWikiLoader(def_config)
    monkeypatch.setattr('nominatim.tools.special_phrases.sp_wiki_loader.SPWikiLoader._get_wiki_content',
                        lambda self, lang: xml_wiki_content)
    return loader


def test_parse_xml(sp_wiki_loader, xml_wiki_content):
    """
        Test method parse_xml()
        Should return the right SpecialPhrase objects.
    """
    phrases = sp_wiki_loader.parse_xml(xml_wiki_content)
    check_phrases_content(phrases)


def test_next(sp_wiki_loader):
    """
        Test objects returned from the next() method.
        It should return all SpecialPhrases objects of
        the 'en' special phrases.
    """
    phrases = next(sp_wiki_loader)
    check_phrases_content(phrases)

def check_phrases_content(phrases):
    """
        Asserts that the given phrases list contains
        the right phrases of the 'en' special phrases.
    """
    assert set((p.p_label, p.p_class, p.p_type, p.p_operator) for p in phrases) ==\
              {('Zip Line', 'aerialway', 'zip_line', '-'),
               ('Zip Lines', 'aerialway', 'zip_line', '-'),
               ('Zip Line in', 'aerialway', 'zip_line', 'in'),
               ('Zip Lines in', 'aerialway', 'zip_line', 'in'),
               ('Zip Line near', 'aerialway', 'zip_line', 'near'),
               ('Animal shelter', 'amenity', 'animal_shelter', '-'),
               ('Animal shelters', 'amenity', 'animal_shelter', '-'),
               ('Animal shelter in', 'amenity', 'animal_shelter', 'in'),
               ('Animal shelters in', 'amenity', 'animal_shelter', 'in'),
               ('Animal shelter near', 'amenity', 'animal_shelter', 'near'),
               ('Animal shelters near', 'amenity', 'animal_shelter', 'near'),
               ('Drinking Water near', 'amenity', 'drinking_water', 'near'),
               ('Water', 'amenity', 'drinking_water', '-'),
               ('Water in', 'amenity', 'drinking_water', 'in'),
               ('Water near', 'amenity', 'drinking_water', 'near'),
               ('Embassy', 'amenity', 'embassy', '-'),
               ('Embassys', 'amenity', 'embassy', '-'),
               ('Embassies', 'amenity', 'embassy', '-')}
