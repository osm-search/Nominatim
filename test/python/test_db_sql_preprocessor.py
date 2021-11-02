"""
Tests for SQL preprocessing.
"""
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

@pytest.mark.parametrize("expr,ret", [
    ("'a'", 'a'),
    ("'{{db.partitions|join}}'", '012'),
    ("{% if 'country_name' in db.tables %}'yes'{% else %}'no'{% endif %}", "yes"),
    ("{% if 'xxx' in db.tables %}'yes'{% else %}'no'{% endif %}", "no"),
    ("'{{db.tablespace.address_data}}'", ""),
    ("'{{db.tablespace.search_data}}'", 'TABLESPACE "dsearch"'),
    ("'{{db.tablespace.address_index}}'", 'TABLESPACE "iaddress"'),
    ("'{{db.tablespace.aux_data}}'", 'TABLESPACE "daux"')
    ])
def test_load_file_simple(sql_preprocessor_cfg, sql_factory,
                          temp_db_conn, temp_db_cursor, monkeypatch,
                          expr, ret):
    monkeypatch.setenv('NOMINATIM_TABLESPACE_SEARCH_DATA', 'dsearch')
    monkeypatch.setenv('NOMINATIM_TABLESPACE_ADDRESS_INDEX', 'iaddress')
    monkeypatch.setenv('NOMINATIM_TABLESPACE_AUX_DATA', 'daux')
    sqlfile = sql_factory("RETURN {};".format(expr))

    SQLPreprocessor(temp_db_conn, sql_preprocessor_cfg).run_sql_file(temp_db_conn, sqlfile)

    assert temp_db_cursor.scalar('SELECT test()') == ret


def test_load_file_with_params(sql_preprocessor, sql_factory, temp_db_conn, temp_db_cursor):
    sqlfile = sql_factory("RETURN '{{ foo }} {{ bar }}';")

    sql_preprocessor.run_sql_file(temp_db_conn, sqlfile, bar='XX', foo='ZZ')

    assert temp_db_cursor.scalar('SELECT test()') == 'ZZ XX'
