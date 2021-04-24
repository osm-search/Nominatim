import importlib
import itertools
import sys
from pathlib import Path

import psycopg2
import psycopg2.extras
import pytest
import tempfile

SRC_DIR = Path(__file__) / '..' / '..' / '..'

# always test against the source
sys.path.insert(0, str(SRC_DIR.resolve()))

from nominatim.config import Configuration
from nominatim.db import connection
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.db import properties

import dummy_tokenizer

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

        return set((tuple(row) for row in self))

    def table_exists(self, table):
        """ Check that a table with the given name exists in the database.
        """
        num = self.scalar("""SELECT count(*) FROM pg_tables
                             WHERE tablename = %s""", (table, ))
        return num == 1

    def table_rows(self, table):
        """ Return the number of rows in the given table.
        """
        return self.scalar('SELECT count(*) FROM ' + table)


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
def dsn(temp_db):
    return 'dbname=' + temp_db


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
    with connection.connect('dbname=' + temp_db) as conn:
        yield conn


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
def table_factory(temp_db_cursor):
    def mk_table(name, definition='id INT', content=None):
        temp_db_cursor.execute('CREATE TABLE {} ({})'.format(name, definition))
        if content is not None:
            if not isinstance(content, str):
                content = '),('.join([str(x) for x in content])
            temp_db_cursor.execute("INSERT INTO {} VALUES ({})".format(name, content))

    return mk_table


@pytest.fixture
def def_config():
    cfg = Configuration(None, SRC_DIR.resolve() / 'settings')
    cfg.set_libdirs(module='.', osm2pgsql='.',
                    php=SRC_DIR / 'lib-php',
                    sql=SRC_DIR / 'lib-sql',
                    data=SRC_DIR / 'data')
    return cfg

@pytest.fixture
def src_dir():
    return SRC_DIR.resolve()

@pytest.fixture
def tmp_phplib_dir():
    with tempfile.TemporaryDirectory() as phpdir:
        (Path(phpdir) / 'admin').mkdir()

        yield Path(phpdir)


@pytest.fixture
def property_table(table_factory):
    table_factory('nominatim_properties', 'property TEXT, value TEXT')

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
                                geom or 'SRID=4326;POINT(0 0)'))

    return _insert

@pytest.fixture
def placex_table(temp_db_with_extensions, temp_db_conn):
    """ Create an empty version of the place table.
    """
    with temp_db_conn.cursor() as cur:
        cur.execute("""CREATE TABLE placex (
                           place_id BIGINT,
                           parent_place_id BIGINT,
                           linked_place_id BIGINT,
                           importance FLOAT,
                           indexed_date TIMESTAMP,
                           geometry_sector INTEGER,
                           rank_address SMALLINT,
                           rank_search SMALLINT,
                           partition SMALLINT,
                           indexed_status SMALLINT,
                           osm_id int8,
                           osm_type char(1),
                           class text,
                           type text,
                           name hstore,
                           admin_level smallint,
                           address hstore,
                           extratags hstore,
                           geometry Geometry(Geometry,4326),
                           wikipedia TEXT,
                           country_code varchar(2),
                           housenumber TEXT,
                           postcode TEXT,
                           centroid GEOMETRY(Geometry, 4326))""")
    temp_db_conn.commit()


@pytest.fixture
def osmline_table(temp_db_with_extensions, temp_db_conn):
    with temp_db_conn.cursor() as cur:
        cur.execute("""CREATE TABLE location_property_osmline (
                           place_id BIGINT,
                           osm_id BIGINT,
                           parent_place_id BIGINT,
                           geometry_sector INTEGER,
                           indexed_date TIMESTAMP,
                           startnumber INTEGER,
                           endnumber INTEGER,
                           partition SMALLINT,
                           indexed_status SMALLINT,
                           linegeo GEOMETRY,
                           interpolationtype TEXT,
                           address HSTORE,
                           postcode TEXT,
                           country_code VARCHAR(2))""")
    temp_db_conn.commit()


@pytest.fixture
def word_table(temp_db, temp_db_conn):
    with temp_db_conn.cursor() as cur:
        cur.execute("""CREATE TABLE word (
                           word_id INTEGER,
                           word_token text,
                           word text,
                           class text,
                           type text,
                           country_code varchar(2),
                           search_name_count INTEGER,
                           operator TEXT)""")
    temp_db_conn.commit()


@pytest.fixture
def osm2pgsql_options(temp_db):
    return dict(osm2pgsql='echo',
                osm2pgsql_cache=10,
                osm2pgsql_style='style.file',
                threads=1,
                dsn='dbname=' + temp_db,
                flatnode_file='',
                tablespaces=dict(slim_data='', slim_index='',
                                 main_data='', main_index=''))

@pytest.fixture
def sql_preprocessor(temp_db_conn, tmp_path, monkeypatch, table_factory):
    table_factory('country_name', 'partition INT', (0, 1, 2))
    cfg = Configuration(None, SRC_DIR.resolve() / 'settings')
    cfg.set_libdirs(module='.', osm2pgsql='.', php=SRC_DIR / 'lib-php',
                    sql=tmp_path, data=SRC_DIR / 'data')

    return SQLPreprocessor(temp_db_conn, cfg)


@pytest.fixture
def tokenizer_mock(monkeypatch, property_table, temp_db_conn):
    """ Sets up the configuration so that the test dummy tokenizer will be
        loaded.
    """
    monkeypatch.setenv('NOMINATIM_TOKENIZER', 'dummy')

    def _import_dummy(module, *args, **kwargs):
        return dummy_tokenizer

    monkeypatch.setattr(importlib, "import_module", _import_dummy)
    properties.set_property(temp_db_conn, 'tokenizer', 'dummy')
