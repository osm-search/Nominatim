"""
Test for various refresh functions.
"""
from pathlib import Path

import pytest

from nominatim.tools import refresh

TEST_DIR = (Path(__file__) / '..' / '..').resolve()

def test_refresh_import_wikipedia_not_existing(dsn):
    assert 1 == refresh.import_wikipedia_articles(dsn, Path('.'))


@pytest.mark.parametrize("replace", (True, False))
def test_refresh_import_wikipedia(dsn, table_factory, temp_db_cursor, replace):
    if replace:
        table_factory('wikipedia_article')
        table_factory('wikipedia_redirect')

    # use the small wikipedia file for the API testdb
    assert 0 == refresh.import_wikipedia_articles(dsn, TEST_DIR / 'testdb')

    assert temp_db_cursor.scalar('SELECT count(*) FROM wikipedia_article') > 0
    assert temp_db_cursor.scalar('SELECT count(*) FROM wikipedia_redirect') > 0
