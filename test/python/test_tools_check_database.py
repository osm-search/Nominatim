"""
Tests for database integrity checks.
"""
import pytest

from nominatim.tools import check_database as chkdb

def test_check_database_unknown_db(def_config, monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 'pgsql:dbname=fjgkhughwgh2423gsags')
    assert 1 == chkdb.check_database(def_config)


def test_check_database_fatal_test(def_config, temp_db):
    assert 1 == chkdb.check_database(def_config)


def test_check_conection_good(temp_db_conn, def_config):
    assert chkdb.check_connection(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_conection_bad(def_config):
    badconn = chkdb._BadConnection('Error')
    assert chkdb.check_connection(badconn, def_config) == chkdb.CheckState.FATAL


def test_check_placex_table_good(temp_db_cursor, temp_db_conn, def_config):
    temp_db_cursor.execute('CREATE TABLE placex (place_id int)')
    assert chkdb.check_placex_table(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_placex_table_bad(temp_db_conn, def_config):
    assert chkdb.check_placex_table(temp_db_conn, def_config) == chkdb.CheckState.FATAL


def test_check_placex_table_size_good(temp_db_cursor, temp_db_conn, def_config):
    temp_db_cursor.execute('CREATE TABLE placex (place_id int)')
    temp_db_cursor.execute('INSERT INTO placex VALUES (1), (2)')
    assert chkdb.check_placex_size(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_placex_table_size_bad(temp_db_cursor, temp_db_conn, def_config):
    temp_db_cursor.execute('CREATE TABLE placex (place_id int)')
    assert chkdb.check_placex_size(temp_db_conn, def_config) == chkdb.CheckState.FATAL


def test_check_module_bad(temp_db_conn, def_config):
    assert chkdb.check_module(temp_db_conn, def_config) == chkdb.CheckState.FAIL


def test_check_indexing_good(temp_db_cursor, temp_db_conn, def_config):
    temp_db_cursor.execute('CREATE TABLE placex (place_id int, indexed_status smallint)')
    temp_db_cursor.execute('INSERT INTO placex VALUES (1, 0), (2, 0)')
    assert chkdb.check_indexing(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_indexing_bad(temp_db_cursor, temp_db_conn, def_config):
    temp_db_cursor.execute('CREATE TABLE placex (place_id int, indexed_status smallint)')
    temp_db_cursor.execute('INSERT INTO placex VALUES (1, 0), (2, 2)')
    assert chkdb.check_indexing(temp_db_conn, def_config) == chkdb.CheckState.FAIL


def test_check_database_indexes_bad(temp_db_conn, def_config):
    assert chkdb.check_database_indexes(temp_db_conn, def_config) == chkdb.CheckState.FAIL


def test_check_tiger_table_disabled(temp_db_conn, def_config, monkeypatch):
    monkeypatch.setenv('NOMINATIM_USE_US_TIGER_DATA' , 'no')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.NOT_APPLICABLE


def test_check_tiger_table_enabled(temp_db_cursor, temp_db_conn, def_config, monkeypatch):
    monkeypatch.setenv('NOMINATIM_USE_US_TIGER_DATA' , 'yes')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.FAIL

    temp_db_cursor.execute('CREATE TABLE location_property_tiger (place_id int)')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.FAIL

    temp_db_cursor.execute('INSERT INTO location_property_tiger VALUES (1), (2)')
    assert chkdb.check_tiger_table(temp_db_conn, def_config) == chkdb.CheckState.OK

