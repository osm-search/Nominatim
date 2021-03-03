"""
Tests for SQL preprocessing.
"""
from pathlib import Path

import pytest

from nominatim.db.sql_preprocessor import SQLPreprocessor

@pytest.fixture
def sql_factory(tmp_path):
    def _mk_sql(sql_body):
        (tmp_path / 'test.sql').write_text("""
          CREATE OR REPLACE FUNCTION test() RETURNS TEXT
          AS $$
          BEGIN
            {}
          END;
          $$ LANGUAGE plpgsql IMMUTABLE;""".format(sql_body))
        return 'test.sql'

    return _mk_sql


@pytest.fixture
def sql_preprocessor(temp_db_conn, tmp_path, def_config, monkeypatch, table_factory):
    monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', '.')
    table_factory('country_name', 'partition INT', (0, 1, 2))
    return SQLPreprocessor(temp_db_conn, def_config, tmp_path)

@pytest.mark.parametrize("expr,ret", [
    ("'a'", 'a'),
    ("'{{db.partitions|join}}'", '012'),
    ("{% if 'country_name' in db.tables %}'yes'{% else %}'no'{% endif %}", "yes"),
    ("{% if 'xxx' in db.tables %}'yes'{% else %}'no'{% endif %}", "no"),
    ("'{{config.DATABASE_MODULE_PATH}}'", '.')
    ])
def test_load_file_simple(sql_preprocessor, sql_factory, temp_db_conn, temp_db_cursor, expr, ret):
    sqlfile = sql_factory("RETURN {};".format(expr))

    sql_preprocessor.run_sql_file(temp_db_conn, sqlfile)

    assert temp_db_cursor.scalar('SELECT test()') == ret


def test_load_file_with_params(sql_preprocessor, sql_factory, temp_db_conn, temp_db_cursor):
    sqlfile = sql_factory("RETURN '{{ foo }} {{ bar }}';")

    sql_preprocessor.run_sql_file(temp_db_conn, sqlfile, bar='XX', foo='ZZ')

    assert temp_db_cursor.scalar('SELECT test()') == 'ZZ XX'
