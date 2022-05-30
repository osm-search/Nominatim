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

@pytest.fixture
def sp_csv_loader(src_dir):
    """
        Return an instance of SPCsvLoader.
    """
    csv_path = (src_dir / 'test' / 'testdata' / 'sp_csv_test.csv').resolve()
    loader = SPCsvLoader(csv_path)
    return loader


def test_generate_phrases(sp_csv_loader):
    """
        Test method parse_csv()
        Should return the right SpecialPhrase objects.
    """
    phrases = list(sp_csv_loader.generate_phrases())

    assert len(phrases) == 41
    assert len(set(phrases)) == 41

    assert any(p.p_label == 'Billboard'
               and p.p_class == 'advertising'
               and p.p_type == 'billboard'
               and p.p_operator == '-' for p in phrases)
    assert any(p.p_label == 'Zip Lines'
               and p.p_class == 'aerialway'
               and p.p_type == 'zip_line'
               and p.p_operator == '-' for p in phrases)


def test_invalid_cvs_file():
    """
        Test method check_csv_validity()
        It should raise an exception when file with a
        different exception than .csv is given.
    """
    loader = SPCsvLoader('test.wrong')

    with pytest.raises(UsageError, match='not a csv file'):
        next(loader.generate_phrases())
