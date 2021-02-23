"""
Tests for functions to import a new database.
"""
import pytest
import psycopg2
import sys

from nominatim.tools import database_import
from nominatim.errors import UsageError

@pytest.fixture
def nonexistant_db():
    dbname = 'test_nominatim_python_unittest'

    conn = psycopg2.connect(database='postgres')

    conn.set_isolation_level(0)
    with conn.cursor() as cur:
        cur.execute('DROP DATABASE IF EXISTS {}'.format(dbname))

    yield dbname

    with conn.cursor() as cur:
        cur.execute('DROP DATABASE IF EXISTS {}'.format(dbname))


def test_create_db_success(nonexistant_db):
    database_import.create_db('dbname=' + nonexistant_db, rouser='www-data')

    conn = psycopg2.connect(database=nonexistant_db)
    conn.close()


def test_create_db_already_exists(temp_db):
    with pytest.raises(UsageError):
        database_import.create_db('dbname=' + temp_db)


def test_create_db_unsupported_version(nonexistant_db, monkeypatch):
    monkeypatch.setattr(database_import, 'POSTGRESQL_REQUIRED_VERSION', (100, 4))

    with pytest.raises(UsageError, match='PostgreSQL server is too old.'):
        database_import.create_db('dbname=' + nonexistant_db)


def test_create_db_missing_ro_user(nonexistant_db):
    with pytest.raises(UsageError, match='Missing read-only user.'):
        database_import.create_db('dbname=' + nonexistant_db, rouser='sdfwkjkjgdugu2;jgsafkljas;')


def test_setup_extensions(temp_db_conn, temp_db_cursor):
    database_import.setup_extensions(temp_db_conn)

    temp_db_cursor.execute('CREATE TABLE t (h HSTORE, geom GEOMETRY(Geometry, 4326))')


def test_setup_extensions_old_postgis(temp_db_conn, monkeypatch):
    monkeypatch.setattr(database_import, 'POSTGIS_REQUIRED_VERSION', (50, 50))

    with pytest.raises(UsageError, match='PostGIS version is too old.'):
        database_import.setup_extensions(temp_db_conn)


def test_install_module(tmp_path):
    src_dir = tmp_path / 'source'
    src_dir.mkdir()
    (src_dir / 'nominatim.so').write_text('TEST nomiantim.so')

    project_dir = tmp_path / 'project'
    project_dir.mkdir()

    database_import.install_module(src_dir, project_dir, '')

    outfile = project_dir / 'module' / 'nominatim.so'

    assert outfile.exists()
    assert outfile.read_text() == 'TEST nomiantim.so'
    assert outfile.stat().st_mode == 33261


def test_import_base_data(src_dir, temp_db, temp_db_cursor):
    temp_db_cursor.execute('CREATE EXTENSION hstore')
    temp_db_cursor.execute('CREATE EXTENSION postgis')
    database_import.import_base_data('dbname=' + temp_db, src_dir / 'data')

    assert temp_db_cursor.scalar('SELECT count(*) FROM country_name') > 0


def test_import_base_data_ignore_partitions(src_dir, temp_db, temp_db_cursor):
    temp_db_cursor.execute('CREATE EXTENSION hstore')
    temp_db_cursor.execute('CREATE EXTENSION postgis')
    database_import.import_base_data('dbname=' + temp_db, src_dir / 'data',
                                     ignore_partitions=True)

    assert temp_db_cursor.scalar('SELECT count(*) FROM country_name') > 0
    assert temp_db_cursor.scalar('SELECT count(*) FROM country_name WHERE partition != 0') == 0
