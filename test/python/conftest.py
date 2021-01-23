import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest

SRC_DIR = Path(__file__) / '..' / '..' / '..'

# always test against the source
sys.path.insert(0, str(SRC_DIR.resolve()))

from nominatim.config import Configuration

class _TestingCursor(psycopg2.extras.DictCursor):
    """ Extension to the DictCursor class that provides execution
        short-cuts that simplify writing assertions.
    """

    def scalar(self, sql, params=None):
        """ Execute a query with a single return value and return this value.
            Raises an assertion when not exactly one row is returned.
        """
        self.execute(sql, params)
        assert self.rowcount == 1
        return self.fetchone()[0]

    def row_set(self, sql, params=None):
        """ Execute a query and return the result as a set of tuples.
        """
        self.execute(sql, params)
        if self.rowcount == 1:
            return set(tuple(self.fetchone()))

        return set((tuple(row) for row in self))

@pytest.fixture
def temp_db(monkeypatch):
    """ Create an empty database for the test. The database name is also
        exported into NOMINATIM_DATABASE_DSN.
    """
    name = 'test_nominatim_python_unittest'
    with psycopg2.connect(database='postgres') as conn:
        conn.set_isolation_level(0)
        with conn.cursor() as cur:
            cur.execute('DROP DATABASE IF EXISTS {}'.format(name))
            cur.execute('CREATE DATABASE {}'.format(name))

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN' , 'dbname=' + name)

    yield name

    with psycopg2.connect(database='postgres') as conn:
        conn.set_isolation_level(0)
        with conn.cursor() as cur:
            cur.execute('DROP DATABASE IF EXISTS {}'.format(name))


@pytest.fixture
def temp_db_conn(temp_db):
    """ Connection to the test database.
    """
    conn = psycopg2.connect(database=temp_db)
    yield conn
    conn.close()


@pytest.fixture
def temp_db_cursor(temp_db):
    """ Connection and cursor towards the test database. The connection will
        be in auto-commit mode.
    """
    conn = psycopg2.connect('dbname=' + temp_db)
    conn.set_isolation_level(0)
    with conn.cursor(cursor_factory=_TestingCursor) as cur:
        yield cur
    conn.close()


@pytest.fixture
def def_config():
    return Configuration(None, SRC_DIR.resolve() / 'settings')
