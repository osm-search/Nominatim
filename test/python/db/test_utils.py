# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for DB utility functions in db.utils
"""
import pytest

import nominatim_db.db.utils as db_utils
from nominatim_db.errors import UsageError


def test_execute_file_success(dsn, temp_db_cursor, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE TABLE test (id INT);\nINSERT INTO test VALUES(56);', encoding='utf-8')

    db_utils.execute_file(dsn, tmpfile)

    assert temp_db_cursor.row_set('SELECT * FROM test') == {(56, )}


def test_execute_file_bad_file(dsn, tmp_path):
    with pytest.raises(FileNotFoundError):
        db_utils.execute_file(dsn, tmp_path / 'test2.sql')


def test_execute_file_bad_sql(dsn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE STABLE test (id INT)', encoding='utf-8')

    with pytest.raises(UsageError):
        db_utils.execute_file(dsn, tmpfile)


def test_execute_file_bad_sql_ignore_errors(dsn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE STABLE test (id INT)', encoding='utf-8')

    db_utils.execute_file(dsn, tmpfile, ignore_errors=True)


def test_execute_file_with_pre_code(dsn, tmp_path, temp_db_cursor):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('INSERT INTO test VALUES(4)', encoding='utf-8')

    db_utils.execute_file(dsn, tmpfile, pre_code='CREATE TABLE test (id INT)')

    assert temp_db_cursor.row_set('SELECT * FROM test') == {(4, )}


def test_execute_file_with_post_code(dsn, tmp_path, temp_db_cursor):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE TABLE test (id INT)', encoding='utf-8')

    db_utils.execute_file(dsn, tmpfile, post_code='INSERT INTO test VALUES(23)')

    assert temp_db_cursor.row_set('SELECT * FROM test') == {(23, )}
