# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
    Tests for methods of the SPCsvLoader class.
"""
import pytest

from nominatim.errors import UsageError
from nominatim.tools.special_phrases.sp_csv_loader import SPCsvLoader

def test_parse_csv(sp_csv_loader):
    """
        Test method parse_csv()
        Should return the right SpecialPhrase objects.
    """
    phrases = sp_csv_loader.parse_csv()
    assert check_phrases_content(phrases)

def test_next(sp_csv_loader):
    """
        Test objects returned from the next() method.
        It should return all SpecialPhrases objects of
        the sp_csv_test.csv special phrases.
    """
    phrases = next(sp_csv_loader)
    assert check_phrases_content(phrases)

def test_check_csv_validity(sp_csv_loader):
    """
        Test method check_csv_validity()
        It should raise an exception when file with a
        different exception than .csv is given.
    """
    sp_csv_loader.csv_path = 'test.csv'
    sp_csv_loader.check_csv_validity()
    sp_csv_loader.csv_path = 'test.wrong'
    with pytest.raises(UsageError):
        assert sp_csv_loader.check_csv_validity()

def check_phrases_content(phrases):
    """
        Asserts that the given phrases list contains
        the right phrases of the sp_csv_test.csv special phrases.
    """
    return  len(phrases) > 1 \
            and any(p.p_label == 'Billboard'
                    and p.p_class == 'advertising'
                    and p.p_type == 'billboard'
                    and p.p_operator == '-' for p in phrases) \
            and any(p.p_label == 'Zip Lines'
                    and p.p_class == 'aerialway'
                    and p.p_type == 'zip_line'
                    and p.p_operator == '-' for p in phrases)

@pytest.fixture
def sp_csv_loader(src_dir):
    """
        Return an instance of SPCsvLoader.
    """
    csv_path = (src_dir / 'test' / 'testdata' / 'sp_csv_test.csv').resolve()
    loader = SPCsvLoader(csv_path)
    return loader
