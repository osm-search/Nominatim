# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for database integrity checks.
"""
import pytest

from nominatim_db.tools import check_database as chkdb
import nominatim_db.version


def test_check_database_unknown_db(def_config, monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 'pgsql:dbname=fjgkhughwgh2423gsags')
    assert chkdb.check_database(def_config) == 1


def test_check_database_fatal_test(def_config, temp_db):
    assert chkdb.check_database(def_config) == 1


def test_check_connection_good(temp_db_conn, def_config):
    assert chkdb.check_connection(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_connection_bad(def_config):
    badconn = chkdb._BadConnection('Error')
    assert chkdb.check_connection(badconn, def_config) == chkdb.CheckState.FATAL


def test_check_database_version_not_found(property_table, temp_db_conn, def_config):
    assert chkdb.check_database_version(temp_db_conn, def_config) == chkdb.CheckState.FATAL


def test_check_database_version_good(property_table, temp_db_conn, def_config):
    property_table.set('database_version',
                       str(nominatim_db.version.NOMINATIM_VERSION))
    assert chkdb.check_database_version(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_database_version_bad(property_table, temp_db_conn, def_config):
    property_table.set('database_version', '3.9.9-9')
    assert chkdb.check_database_version(temp_db_conn, def_config) == chkdb.CheckState.FATAL


def test_check_placex_table_good(placex_table, temp_db_conn, def_config):
    assert chkdb.check_placex_table(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_placex_table_bad(temp_db_conn, def_config):
    assert chkdb.check_placex_table(temp_db_conn, def_config) == chkdb.CheckState.FATAL


def test_check_placex_table_size_good(placex_row, temp_db_conn, def_config):
    for _ in range(2):
        placex_row()
    assert chkdb.check_placex_size(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_placex_table_size_bad(placex_table, temp_db_conn, def_config):
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


def test_check_duplicate_partial_terms_no_word_table(temp_db_conn, def_config):
    assert chkdb.check_duplicate_partial_terms(temp_db_conn, def_config) \
        == chkdb.CheckState.NOT_APPLICABLE


@pytest.mark.parametrize("words,state", [
    ([], chkdb.CheckState.OK),
    ([(1, 'foo', 'w'), (2, 'bar', 'w'), (3, 'foo', 'W')], chkdb.CheckState.OK),
    ([(1, 'foo', 'w'), (2, 'bar', 'w'), (3, 'foo', 'w')], chkdb.CheckState.FAIL)])
def test_check_duplicate_partial_terms(temp_db_cursor, temp_db_conn, def_config,
                                       words, state):
    temp_db_cursor.execute("""CREATE TABLE word (word_id INTEGER, word_token text NOT NULL,
                                                 type text NOT NULL, word text, info jsonb)""")
    for word in words:
        temp_db_cursor.execute('INSERT INTO word (word_id, word_token, type) VALUES (%s, %s, %s)',
                               word)

    assert chkdb.check_duplicate_partial_terms(temp_db_conn, def_config) == state


def test_check_indexing_good(placex_row, temp_db_conn, def_config):
    for _ in range(2):
        placex_row(indexed_status=0)
    assert chkdb.check_indexing(temp_db_conn, def_config) == chkdb.CheckState.OK


def test_check_indexing_bad(placex_row, temp_db_conn, def_config):
    for status in (0, 2):
        placex_row(indexed_status=status)
    assert chkdb.check_indexing(temp_db_conn, def_config) == chkdb.CheckState.FAIL


def test_check_indexing_bad_frozen(placex_row, temp_db_conn, def_config):
    for status in (0, 2):
        placex_row(indexed_status=status)
    temp_db_conn.execute('DROP TABLE place')
    assert chkdb.check_indexing(temp_db_conn, def_config) == chkdb.CheckState.WARN


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
