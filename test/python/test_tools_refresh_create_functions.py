"""
Tests for creating PL/pgSQL functions for Nominatim.
"""
import pytest

from nominatim.tools.refresh import create_functions

@pytest.fixture
def conn(temp_db_conn, table_factory, monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', '.')
    table_factory('country_name', 'partition INT', (0, 1, 2))
    return temp_db_conn


def test_create_functions(temp_db_cursor, conn, def_config, tmp_path):
    sqlfile = tmp_path / 'functions.sql'
    sqlfile.write_text("""CREATE OR REPLACE FUNCTION test() RETURNS INTEGER
                          AS $$
                          BEGIN
                            RETURN 43;
                          END;
                          $$ LANGUAGE plpgsql IMMUTABLE;
                       """)

    create_functions(conn, def_config, tmp_path)

    assert temp_db_cursor.scalar('SELECT test()') == 43


@pytest.mark.parametrize("dbg,ret", ((True, 43), (False, 22)))
def test_create_functions_with_template(temp_db_cursor, conn, def_config, tmp_path, dbg, ret):
    sqlfile = tmp_path / 'functions.sql'
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

    create_functions(conn, def_config, tmp_path, enable_debug=dbg)

    assert temp_db_cursor.scalar('SELECT test()') == ret
