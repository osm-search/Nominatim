# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for specialised conenction and cursor classes.
"""
import pytest
import psycopg2

from nominatim.db.connection import connect, get_pg_env

@pytest.fixture
def db(dsn):
    with connect(dsn) as conn:
        yield conn


def test_connection_table_exists(db, table_factory):
    assert not db.table_exists('foobar')

    table_factory('foobar')

    assert db.table_exists('foobar')


def test_has_column_no_table(db):
    assert not db.table_has_column('sometable', 'somecolumn')


@pytest.mark.parametrize('name,result', [('tram', True), ('car', False)])
def test_has_column(db, table_factory, name, result):
    table_factory('stuff', 'tram TEXT')

    assert db.table_has_column('stuff', name) == result

def test_connection_index_exists(db, table_factory, temp_db_cursor):
    assert not db.index_exists('some_index')

    table_factory('foobar')
    temp_db_cursor.execute('CREATE INDEX some_index ON foobar(id)')

    assert db.index_exists('some_index')
    assert db.index_exists('some_index', table='foobar')
    assert not db.index_exists('some_index', table='bar')


def test_drop_table_existing(db, table_factory):
    table_factory('dummy')
    assert db.table_exists('dummy')

    db.drop_table('dummy')
    assert not db.table_exists('dummy')


def test_drop_table_non_existsing(db):
    db.drop_table('dfkjgjriogjigjgjrdghehtre')


def test_drop_table_non_existing_force(db):
    with pytest.raises(psycopg2.ProgrammingError, match='.*does not exist.*'):
        db.drop_table('dfkjgjriogjigjgjrdghehtre', if_exists=False)

def test_connection_server_version_tuple(db):
    ver = db.server_version_tuple()

    assert isinstance(ver, tuple)
    assert len(ver) == 2
    assert ver[0] > 8


def test_connection_postgis_version_tuple(db, temp_db_with_extensions):
    ver = db.postgis_version_tuple()

    assert isinstance(ver, tuple)
    assert len(ver) == 2
    assert ver[0] >= 2


def test_cursor_scalar(db, table_factory):
    table_factory('dummy')

    with db.cursor() as cur:
        assert cur.scalar('SELECT count(*) FROM dummy') == 0


def test_cursor_scalar_many_rows(db):
    with db.cursor() as cur:
        with pytest.raises(RuntimeError):
            cur.scalar('SELECT * FROM pg_tables')


def test_cursor_scalar_no_rows(db, table_factory):
    table_factory('dummy')

    with db.cursor() as cur:
        with pytest.raises(RuntimeError):
            cur.scalar('SELECT id FROM dummy')


def test_get_pg_env_add_variable(monkeypatch):
    monkeypatch.delenv('PGPASSWORD', raising=False)
    env = get_pg_env('user=fooF')

    assert env['PGUSER'] == 'fooF'
    assert 'PGPASSWORD' not in env


def test_get_pg_env_overwrite_variable(monkeypatch):
    monkeypatch.setenv('PGUSER', 'some default')
    env = get_pg_env('user=overwriter')

    assert env['PGUSER'] == 'overwriter'


def test_get_pg_env_ignore_unknown():
    env = get_pg_env('client_encoding=stuff', base_env={})

    assert env == {}
