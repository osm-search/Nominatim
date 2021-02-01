import itertools
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest

SRC_DIR = Path(__file__) / '..' / '..' / '..'

# always test against the source
sys.path.insert(0, str(SRC_DIR.resolve()))

from nominatim.config import Configuration
from nominatim.db import connection

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
    conn = psycopg2.connect(database='postgres')

    conn.set_isolation_level(0)
    with conn.cursor() as cur:
        cur.execute('DROP DATABASE IF EXISTS {}'.format(name))
        cur.execute('CREATE DATABASE {}'.format(name))

    conn.close()

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN' , 'dbname=' + name)

    yield name

    conn = psycopg2.connect(database='postgres')

    conn.set_isolation_level(0)
    with conn.cursor() as cur:
        cur.execute('DROP DATABASE IF EXISTS {}'.format(name))

    conn.close()

@pytest.fixture
def temp_db_with_extensions(temp_db):
    conn = psycopg2.connect(database=temp_db)
    with conn.cursor() as cur:
        cur.execute('CREATE EXTENSION hstore; CREATE EXTENSION postgis;')
    conn.commit()
    conn.close()

    return temp_db

@pytest.fixture
def temp_db_conn(temp_db):
    """ Connection to the test database.
    """
    conn = connection.connect('dbname=' + temp_db)
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


@pytest.fixture
def status_table(temp_db_conn):
    """ Create an empty version of the status table and
        the status logging table.
    """
    with temp_db_conn.cursor() as cur:
        cur.execute("""CREATE TABLE import_status (
                           lastimportdate timestamp with time zone NOT NULL,
                           sequence_id integer,
                           indexed boolean
                       )""")
        cur.execute("""CREATE TABLE import_osmosis_log (
                           batchend timestamp,
                           batchseq integer,
                           batchsize bigint,
                           starttime timestamp,
                           endtime timestamp,
                           event text
                           )""")
    temp_db_conn.commit()


@pytest.fixture
def place_table(temp_db_with_extensions, temp_db_conn):
    """ Create an empty version of the place table.
    """
    with temp_db_conn.cursor() as cur:
        cur.execute("""CREATE TABLE place (
                           osm_id int8 NOT NULL,
                           osm_type char(1) NOT NULL,
                           class text NOT NULL,
                           type text NOT NULL,
                           name hstore,
                           admin_level smallint,
                           address hstore,
                           extratags hstore,
                           geometry Geometry(Geometry,4326) NOT NULL)""")
    temp_db_conn.commit()


@pytest.fixture
def place_row(place_table, temp_db_cursor):
    """ A factory for rows in the place table. The table is created as a
        prerequisite to the fixture.
    """
    idseq = itertools.count(1001)
    def _insert(osm_type='N', osm_id=None, cls='amenity', typ='cafe', names=None,
                admin_level=None, address=None, extratags=None, geom=None):
        temp_db_cursor.execute("INSERT INTO place VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                               (osm_id or next(idseq), osm_type, cls, typ, names,
                                admin_level, address, extratags,
                                geom or 'SRID=4326;POINT(0 0 )'))

    return _insert
