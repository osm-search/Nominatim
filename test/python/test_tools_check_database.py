"""
Tests for database integrity checks.
"""
import pytest

from nominatim.tools import check_database as chkdb

def test_check_database_unknown_db(def_config, monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 'pgsql:dbname=fjgkhughwgh2423gsags')
    assert chkdb.check_database(def_config) == 1


def test_check_database_fatal_test(def_config, temp_db):
    assert chkdb.check_database(def_config) == 1


def test_check_conection_good(temp_db_conn, def_config):
    assert chkdb.check_connection(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_conection_bad(def_config):
    badconn = chkdb._BadConnection('Error')
    assert chkdb.check_connection(badconn, def_config) == chkdb.CheckState.FATAL


def test_check_placex_table_good(table_factory, temp_db_conn, def_config):
    table_factory('placex')
    assert chkdb.check_placex_table(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_placex_table_bad(temp_db_conn, def_config):
    assert chkdb.check_placex_table(temp_db_conn, def_config) == chkdb.CheckState.FATAL


def test_check_placex_table_size_good(table_factory, temp_db_conn, def_config):
    table_factory('placex', content=((1, ), (2, )))
    assert chkdb.check_placex_size(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_placex_table_size_bad(table_factory, temp_db_conn, def_config):
    table_factory('placex')
    assert chkdb.check_placex_size(temp_db_conn, def_config) == chkdb.CheckState.FATAL


def test_check_tokenizer_missing(temp_db_conn, def_config, tmp_path):
    def_config.project_dir = tmp_path
    assert chkdb.check_tokenizer(temp_db_conn, def_config) == chkdb.CheckState.FAIL


@pytest.mark.parametrize("check_result,state", [(None, chkdb.CheckState.OK),
                                                ("Something wrong", chkdb.CheckState.FAIL)])
def test_check_tokenizer(temp_db_conn, def_config, monkeypatch,
                         check_result, state):
    class _TestTokenizer:
        @staticmethod
        def check_database(_):
            return check_result

    monkeypatch.setattr(chkdb.tokenizer_factory, 'get_tokenizer_for_db',
                        lambda *a, **k: _TestTokenizer())
    assert chkdb.check_tokenizer(temp_db_conn, def_config) == state


def test_check_indexing_good(table_factory, temp_db_conn, def_config):
    table_factory('placex', 'place_id int, indexed_status smallint',
                  content=((1, 0), (2, 0)))
    assert chkdb.check_indexing(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_indexing_bad(table_factory, temp_db_conn, def_config):
    table_factory('placex', 'place_id int, indexed_status smallint',
                  content=((1, 0), (2, 2)))
    assert chkdb.check_indexing(temp_db_conn, def_config) == chkdb.CheckState.FAIL


def test_check_database_indexes_bad(temp_db_conn, def_config):
    assert chkdb.check_database_indexes(temp_db_conn, def_config) == chkdb.CheckState.FAIL


def test_check_database_indexes_valid(temp_db_conn, def_config):
    assert chkdb.check_database_index_valid(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_tiger_table_disabled(temp_db_conn, def_config, monkeypatch):
    monkeypatch.setenv('NOMINATIM_USE_US_TIGER_DATA', 'no')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.NOT_APPLICABLE


def test_check_tiger_table_enabled(temp_db_cursor, temp_db_conn, def_config, monkeypatch):
    monkeypatch.setenv('NOMINATIM_USE_US_TIGER_DATA', 'yes')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.FAIL

    temp_db_cursor.execute('CREATE TABLE location_property_tiger (place_id int)')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.FAIL

    temp_db_cursor.execute('INSERT INTO location_property_tiger VALUES (1), (2)')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.OK
