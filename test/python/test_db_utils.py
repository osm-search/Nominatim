"""
Tests for DB utility functions in db.utils
"""
import psycopg2
import pytest

import nominatim.db.utils as db_utils
from nominatim.errors import UsageError

@pytest.fixture
def dsn(temp_db):
    return 'dbname=' + temp_db

def test_execute_file_success(dsn, temp_db_cursor, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE TABLE test (id INT);\nINSERT INTO test VALUES(56);')

    db_utils.execute_file(dsn, tmpfile)

    temp_db_cursor.execute('SELECT * FROM test')

    assert temp_db_cursor.rowcount == 1
    assert temp_db_cursor.fetchone()[0] == 56

def test_execute_file_bad_file(dsn, tmp_path):
    with pytest.raises(FileNotFoundError):
        db_utils.execute_file(dsn, tmp_path / 'test2.sql')


def test_execute_file_bad_sql(dsn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE STABLE test (id INT)')

    with pytest.raises(UsageError):
        db_utils.execute_file(dsn, tmpfile)


def test_execute_file_bad_sql_ignore_errors(dsn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE STABLE test (id INT)')

    db_utils.execute_file(dsn, tmpfile, ignore_errors=True)
