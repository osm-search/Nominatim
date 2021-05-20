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
    loader = SPWikiLoader(def_config, ['en'])
    monkeypatch.setattr('nominatim.tools.special_phrases.sp_wiki_loader.SPWikiLoader._get_wiki_content',
                        lambda self, lang: xml_wiki_content)
    return loader


def test_parse_xml(sp_wiki_loader, xml_wiki_content):
    """
        Test method parse_xml()
        Should return the right SpecialPhrase objects.
    """
    phrases = sp_wiki_loader.parse_xml(xml_wiki_content)
    assert check_phrases_content(phrases)


def test_next(sp_wiki_loader):
    """
        Test objects returned from the next() method.
        It should return all SpecialPhrases objects of
        the 'en' special phrases.
    """
    phrases = next(sp_wiki_loader)
    assert check_phrases_content(phrases)

def check_phrases_content(phrases):
    """
        Asserts that the given phrases list contains
        the right phrases of the 'en' special phrases.
    """
    return  len(phrases) > 1 \
            and any(p.p_label == 'Embassies' and p.p_class == 'amenity' and p.p_type == 'embassy'
                    and p.p_operator == '-' for p in phrases) \
            and any(p.p_label == 'Zip Line' and p.p_class == 'aerialway' and p.p_type == 'zip_line'
                    and p.p_operator == '-' for p in phrases)
