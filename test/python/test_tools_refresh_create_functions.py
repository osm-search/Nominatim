"""
Tests for creating PL/pgSQL functions for Nominatim.
"""
from pathlib import Path
import pytest

from nominatim.db.connection import connect
from nominatim.tools.refresh import _get_standard_function_sql, _get_partition_function_sql

SQL_DIR = (Path(__file__) / '..' / '..' / '..' / 'lib-sql').resolve()

@pytest.fixture
def db(temp_db):
    with connect('dbname=' + temp_db) as conn:
        yield conn

@pytest.fixture
def db_with_tables(db):
    with db.cursor() as cur:
        for table in ('place', 'placex', 'location_postcode'):
            cur.execute('CREATE TABLE {} (place_id BIGINT)'.format(table))

    return db


def test_standard_functions_replace_module_default(db, def_config):
    def_config.project_dir = Path('.')
    sql = _get_standard_function_sql(db, def_config, SQL_DIR, False, False)

    assert sql
    assert sql.find('{modulepath}') < 0
    assert sql.find("'{}'".format(Path('module/nominatim.so').resolve())) >= 0


def test_standard_functions_replace_module_custom(monkeypatch, db, def_config):
    monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', 'custom')
    sql = _get_standard_function_sql(db, def_config, SQL_DIR, False, False)

    assert sql
    assert sql.find('{modulepath}') < 0
    assert sql.find("'custom/nominatim.so'") >= 0


@pytest.mark.parametrize("enabled", (True, False))
def test_standard_functions_enable_diff(db_with_tables, def_config, enabled):
    def_config.project_dir = Path('.')
    sql = _get_standard_function_sql(db_with_tables, def_config, SQL_DIR, enabled, False)

    assert sql
    assert (sql.find('%DIFFUPDATES%') < 0) == enabled


@pytest.mark.parametrize("enabled", (True, False))
def test_standard_functions_enable_debug(db_with_tables, def_config, enabled):
    def_config.project_dir = Path('.')
    sql = _get_standard_function_sql(db_with_tables, def_config, SQL_DIR, False, enabled)

    assert sql
    assert (sql.find('--DEBUG') < 0) == enabled


@pytest.mark.parametrize("enabled", (True, False))
def test_standard_functions_enable_limit_reindexing(monkeypatch, db_with_tables, def_config, enabled):
    def_config.project_dir = Path('.')
    monkeypatch.setenv('NOMINATIM_LIMIT_REINDEXING', 'yes' if enabled else 'no')
    sql = _get_standard_function_sql(db_with_tables, def_config, SQL_DIR, False, False)

    assert sql
    assert (sql.find('--LIMIT INDEXING') < 0) == enabled


@pytest.mark.parametrize("enabled", (True, False))
def test_standard_functions_enable_tiger(monkeypatch, db_with_tables, def_config, enabled):
    def_config.project_dir = Path('.')
    monkeypatch.setenv('NOMINATIM_USE_US_TIGER_DATA', 'yes' if enabled else 'no')
    sql = _get_standard_function_sql(db_with_tables, def_config, SQL_DIR, False, False)

    assert sql
    assert (sql.find('%NOTIGERDATA%') >= 0) == enabled


@pytest.mark.parametrize("enabled", (True, False))
def test_standard_functions_enable_aux(monkeypatch, db_with_tables, def_config, enabled):
    def_config.project_dir = Path('.')
    monkeypatch.setenv('NOMINATIM_USE_AUX_LOCATION_DATA', 'yes' if enabled else 'no')
    sql = _get_standard_function_sql(db_with_tables, def_config, SQL_DIR, False, False)

    assert sql
    assert (sql.find('%NOAUXDATA%') >= 0) == enabled


def test_partition_function(temp_db_cursor, db, def_config):
    temp_db_cursor.execute("CREATE TABLE country_name (partition SMALLINT)")

    sql = _get_partition_function_sql(db, SQL_DIR)

    assert sql
    assert sql.find('-partition-') < 0
