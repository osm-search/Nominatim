"""
Tests for DB utility functions in db.utils
"""
import psycopg2
import pytest

import nominatim.db.utils as db_utils

def test_execute_file_success(temp_db_conn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE TABLE test (id INT);\nINSERT INTO test VALUES(56);')

    db_utils.execute_file(temp_db_conn, tmpfile)

    with temp_db_conn.cursor() as cur:
        cur.execute('SELECT * FROM test')

        assert cur.rowcount == 1
        assert cur.fetchone()[0] == 56

def test_execute_file_bad_file(temp_db_conn, tmp_path):
    with pytest.raises(FileNotFoundError):
        db_utils.execute_file(temp_db_conn, tmp_path / 'test2.sql')

def test_execute_file_bad_sql(temp_db_conn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE STABLE test (id INT)')

    with pytest.raises(psycopg2.ProgrammingError):
        db_utils.execute_file(temp_db_conn, tmpfile)
