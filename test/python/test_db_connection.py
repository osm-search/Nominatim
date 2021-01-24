"""
Tests for specialised conenction and cursor classes.
"""
import pytest

from nominatim.db.connection import connect

@pytest.fixture
def db(temp_db):
    conn = connect('dbname=' + temp_db)
    yield conn
    conn.close()


def test_connection_table_exists(db, temp_db_cursor):
    assert db.table_exists('foobar') == False

    temp_db_cursor.execute('CREATE TABLE foobar (id INT)')

    assert db.table_exists('foobar') == True


def test_cursor_scalar(db, temp_db_cursor):
    temp_db_cursor.execute('CREATE TABLE dummy (id INT)')

    with db.cursor() as cur:
        assert cur.scalar('SELECT count(*) FROM dummy') == 0

def test_cursor_scalar_many_rows(db):
    with db.cursor() as cur:
        with pytest.raises(ValueError):
            cur.scalar('SELECT * FROM pg_tables')
