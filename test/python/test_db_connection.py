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


def test_connection_index_exists(db, temp_db_cursor):
    assert db.index_exists('some_index') == False

    temp_db_cursor.execute('CREATE TABLE foobar (id INT)')
    temp_db_cursor.execute('CREATE INDEX some_index ON foobar(id)')

    assert db.index_exists('some_index') == True
    assert db.index_exists('some_index', table='foobar') == True
    assert db.index_exists('some_index', table='bar') == False


def test_connection_server_version_tuple(db):
    ver = db.server_version_tuple()

    assert isinstance(ver, tuple)
    assert len(ver) == 2
    assert ver[0] > 8

def test_cursor_scalar(db, temp_db_cursor):
    temp_db_cursor.execute('CREATE TABLE dummy (id INT)')

    with db.cursor() as cur:
        assert cur.scalar('SELECT count(*) FROM dummy') == 0


def test_cursor_scalar_many_rows(db):
    with db.cursor() as cur:
        with pytest.raises(RuntimeError):
            cur.scalar('SELECT * FROM pg_tables')
