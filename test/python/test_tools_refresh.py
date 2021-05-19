"""
Test for various refresh functions.
"""
from pathlib import Path

import pytest

from nominatim.tools import refresh

def test_refresh_import_wikipedia_not_existing(dsn):
    assert 1 == refresh.import_wikipedia_articles(dsn, Path('.'))


@pytest.mark.parametrize("replace", (True, False))
def test_refresh_import_wikipedia(dsn, src_dir, table_factory, temp_db_cursor, replace):
    if replace:
        table_factory('wikipedia_article')
        table_factory('wikipedia_redirect')

    # use the small wikipedia file for the API testdb
    assert 0 == refresh.import_wikipedia_articles(dsn, src_dir / 'test' / 'testdb')

    assert temp_db_cursor.table_rows('wikipedia_article') > 0
    assert temp_db_cursor.table_rows('wikipedia_redirect') > 0
