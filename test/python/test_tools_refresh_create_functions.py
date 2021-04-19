"""
Tests for creating PL/pgSQL functions for Nominatim.
"""
import pytest

from nominatim.tools.refresh import create_functions

@pytest.fixture
def sql_tmp_path(tmp_path, def_config):
    def_config.lib_dir.sql = tmp_path
    return tmp_path

@pytest.fixture
def conn(temp_db_conn, table_factory, monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', '.')
    table_factory('country_name', 'partition INT', (0, 1, 2))
    return temp_db_conn


def test_create_functions(temp_db_cursor, conn, def_config, sql_tmp_path):
    sqlfile = sql_tmp_path / 'functions.sql'
    sqlfile.write_text("""CREATE OR REPLACE FUNCTION test() RETURNS INTEGER
                          AS $$
                          BEGIN
                            RETURN 43;
                          END;
                          $$ LANGUAGE plpgsql IMMUTABLE;
                       """)

    create_functions(conn, def_config)

    assert temp_db_cursor.scalar('SELECT test()') == 43


@pytest.mark.parametrize("dbg,ret", ((True, 43), (False, 22)))
def test_create_functions_with_template(temp_db_cursor, conn, def_config, sql_tmp_path, dbg, ret):
    sqlfile = sql_tmp_path / 'functions.sql'
    sqlfile.write_text("""CREATE OR REPLACE FUNCTION test() RETURNS INTEGER
                          AS $$
                          BEGIN
                            {% if debug %}
                            RETURN 43;
                            {% else %}
                            RETURN 22;
                            {% endif %}
                          END;
                          $$ LANGUAGE plpgsql IMMUTABLE;
                       """)

    create_functions(conn, def_config, enable_debug=dbg)

    assert temp_db_cursor.scalar('SELECT test()') == ret
