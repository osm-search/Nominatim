"""
Tests for DB utility functions in db.utils
"""
import pytest

import nominatim.db.utils as db_utils
from nominatim.errors import UsageError

def test_execute_file_success(dsn, temp_db_cursor, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE TABLE test (id INT);\nINSERT INTO test VALUES(56);')

    db_utils.execute_file(dsn, tmpfile)

    assert temp_db_cursor.row_set('SELECT * FROM test') == {(56, )}

def test_execute_file_bad_file(dsn, tmp_path):
    with pytest.raises(FileNotFoundError):
        db_utils.execute_file(dsn, tmp_path / 'test2.sql')


def test_execute_file_bad_sql(dsn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE STABLE test (id INT)')

    with pytest.raises(UsageError):
        db_utils.execute_file(dsn, tmpfile)


def test_execute_file_bad_sql_ignore_errors(dsn, tmp_path):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE STABLE test (id INT)')

    db_utils.execute_file(dsn, tmpfile, ignore_errors=True)


def test_execute_file_with_pre_code(dsn, tmp_path, temp_db_cursor):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('INSERT INTO test VALUES(4)')

    db_utils.execute_file(dsn, tmpfile, pre_code='CREATE TABLE test (id INT)')

    assert temp_db_cursor.row_set('SELECT * FROM test') == {(4, )}


def test_execute_file_with_post_code(dsn, tmp_path, temp_db_cursor):
    tmpfile = tmp_path / 'test.sql'
    tmpfile.write_text('CREATE TABLE test (id INT)')

    db_utils.execute_file(dsn, tmpfile, post_code='INSERT INTO test VALUES(23)')

    assert temp_db_cursor.row_set('SELECT * FROM test') == {(23, )}


class TestCopyBuffer:
    TABLE_NAME = 'copytable'

    @pytest.fixture(autouse=True)
    def setup_test_table(self, table_factory):
        table_factory(self.TABLE_NAME, 'colA INT, colB TEXT')


    def table_rows(self, cursor):
        return cursor.row_set('SELECT * FROM ' + self.TABLE_NAME)


    def test_copybuffer_empty(self):
        with db_utils.CopyBuffer() as buf:
            buf.copy_out(None, "dummy")


    def test_all_columns(self, temp_db_cursor):
        with db_utils.CopyBuffer() as buf:
            buf.add(3, 'hum')
            buf.add(None, 'f\\t')

            buf.copy_out(temp_db_cursor, self.TABLE_NAME)

        assert self.table_rows(temp_db_cursor) == {(3, 'hum'), (None, 'f\\t')}


    def test_selected_columns(self, temp_db_cursor):
        with db_utils.CopyBuffer() as buf:
            buf.add('foo')

            buf.copy_out(temp_db_cursor, self.TABLE_NAME,
                         columns=['colB'])

        assert self.table_rows(temp_db_cursor) == {(None, 'foo')}


    def test_reordered_columns(self, temp_db_cursor):
        with db_utils.CopyBuffer() as buf:
            buf.add('one', 1)
            buf.add(' two ', 2)

            buf.copy_out(temp_db_cursor, self.TABLE_NAME,
                         columns=['colB', 'colA'])

        assert self.table_rows(temp_db_cursor) == {(1, 'one'), (2, ' two ')}


    def test_special_characters(self, temp_db_cursor):
        with db_utils.CopyBuffer() as buf:
            buf.add('foo\tbar')
            buf.add('sun\nson')
            buf.add('\\N')

            buf.copy_out(temp_db_cursor, self.TABLE_NAME,
                         columns=['colB'])

        assert self.table_rows(temp_db_cursor) == {(None, 'foo\tbar'),
                                                   (None, 'sun\nson'),
                                                   (None, '\\N')}



