import itertools
import sys
import tempfile
from pathlib import Path

import psycopg2
import pytest

SRC_DIR = Path(__file__) / '..' / '..' / '..'

# always test against the source
sys.path.insert(0, str(SRC_DIR.resolve()))

from nominatim.config import Configuration
from nominatim.db import connection
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.db import properties
import nominatim.tokenizer.factory

import dummy_tokenizer
import mocks
from cursor import CursorForTesting


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

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 'dbname=' + name)

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
    with conn.cursor(cursor_factory=CursorForTesting) as cur:
        yield cur
    conn.close()


@pytest.fixture
def table_factory(temp_db_cursor):
    def mk_table(name, definition='id INT', content=None):
        temp_db_cursor.execute('CREATE TABLE {} ({})'.format(name, definition))
        if content is not None:
            temp_db_cursor.execute_values("INSERT INTO {} VALUES %s".format(name), content)

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
    return mocks.MockPlacexTable(temp_db_conn)


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
def word_table(temp_db_conn):
    return mocks.MockWordTable(temp_db_conn)


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
    table_factory('country_name', 'partition INT', ((0, ), (1, ), (2, )))
    cfg = Configuration(None, SRC_DIR.resolve() / 'settings')
    cfg.set_libdirs(module='.', osm2pgsql='.', php=SRC_DIR / 'lib-php',
                    sql=tmp_path, data=SRC_DIR / 'data')

    return SQLPreprocessor(temp_db_conn, cfg)


@pytest.fixture
def tokenizer_mock(monkeypatch, property_table, temp_db_conn, tmp_path):
    """ Sets up the configuration so that the test dummy tokenizer will be
        loaded when the tokenizer factory is used. Also returns a factory
        with which a new dummy tokenizer may be created.
    """
    monkeypatch.setenv('NOMINATIM_TOKENIZER', 'dummy')

    def _import_dummy(module, *args, **kwargs):
        return dummy_tokenizer

    monkeypatch.setattr(nominatim.tokenizer.factory, "_import_tokenizer", _import_dummy)
    properties.set_property(temp_db_conn, 'tokenizer', 'dummy')

    def _create_tokenizer():
        return dummy_tokenizer.DummyTokenizer(None, None)

    return _create_tokenizer
