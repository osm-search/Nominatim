"""
Tests for replication command of command-line interface wrapper.
"""
import datetime as dt
import time
from pathlib import Path

import pytest

import nominatim.cli
import nominatim.indexer.indexer
import nominatim.tools.replication
from nominatim.db import status

from mocks import MockParamCapture

SRC_DIR = (Path(__file__) / '..' / '..' / '..').resolve()

def call_nominatim(*args):
    return nominatim.cli.nominatim(module_dir='build/module',
                                   osm2pgsql_path='build/osm2pgsql/osm2pgsql',
                                   phplib_dir=str(SRC_DIR / 'lib-php'),
                                   data_dir=str(SRC_DIR / 'data'),
                                   phpcgi_path='/usr/bin/php-cgi',
                                   sqllib_dir=str(SRC_DIR / 'lib-sql'),
                                   config_dir=str(SRC_DIR / 'settings'),
                                   cli_args=['replication'] + list(args))

@pytest.fixture
def tokenizer_mock(monkeypatch):
    class DummyTokenizer:
        def __init__(self, *args, **kwargs):
            self.update_sql_functions_called = False
            self.finalize_import_called = False

        def update_sql_functions(self, *args):
            self.update_sql_functions_called = True

        def finalize_import(self, *args):
            self.finalize_import_called = True

    tok = DummyTokenizer()
    monkeypatch.setattr(nominatim.tokenizer.factory, 'get_tokenizer_for_db' ,
                        lambda *args: tok)
    monkeypatch.setattr(nominatim.tokenizer.factory, 'create_tokenizer' ,
                        lambda *args: tok)

    return tok


@pytest.fixture
def index_mock(monkeypatch, tokenizer_mock):
    mock = MockParamCapture()
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_boundaries', mock)
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_by_rank', mock)

    return mock


@pytest.fixture
def mock_func_factory(monkeypatch):
    def get_mock(module, func):
        mock = MockParamCapture()
        monkeypatch.setattr(module, func, mock)
        return mock

    return get_mock


@pytest.fixture
def init_status(temp_db_conn, status_table):
    status.set_status(temp_db_conn, date=dt.datetime.now(dt.timezone.utc), seq=1)
    return 1


@pytest.fixture
def update_mock(mock_func_factory, init_status, tokenizer_mock):
    return mock_func_factory(nominatim.tools.replication, 'update')

@pytest.mark.parametrize("params,func", [
                         (('--init', '--no-update-functions'), 'init_replication'),
                         (('--check-for-updates',), 'check_for_updates')
                         ])
def test_replication_command(mock_func_factory, temp_db, params, func):
    func_mock = mock_func_factory(nominatim.tools.replication, func)

    assert 0 == call_nominatim(*params)
    assert func_mock.called == 1


def test_replication_update_bad_interval(monkeypatch, temp_db):
    monkeypatch.setenv('NOMINATIM_REPLICATION_UPDATE_INTERVAL', 'xx')

    assert call_nominatim() == 1


def test_replication_update_bad_interval_for_geofabrik(monkeypatch, temp_db):
    monkeypatch.setenv('NOMINATIM_REPLICATION_URL',
                       'https://download.geofabrik.de/europe/ireland-and-northern-ireland-updates')

    assert call_nominatim() == 1


def test_replication_update_once_no_index(update_mock):
    assert 0 == call_nominatim('--once', '--no-index')

    assert str(update_mock.last_args[1]['osm2pgsql']) == 'build/osm2pgsql/osm2pgsql'


def test_replication_update_custom_osm2pgsql(monkeypatch, update_mock):
    monkeypatch.setenv('NOMINATIM_OSM2PGSQL_BINARY', '/secret/osm2pgsql')
    assert 0 == call_nominatim('--once', '--no-index')

    assert str(update_mock.last_args[1]['osm2pgsql']) == '/secret/osm2pgsql'


def test_replication_update_custom_threads(update_mock):
    assert 0 == call_nominatim('--once', '--no-index', '--threads', '4')

    assert update_mock.last_args[1]['threads'] == 4


def test_replication_update_continuous(monkeypatch, init_status, index_mock):
    states = [nominatim.tools.replication.UpdateState.UP_TO_DATE,
              nominatim.tools.replication.UpdateState.UP_TO_DATE]
    monkeypatch.setattr(nominatim.tools.replication, 'update',
                        lambda *args, **kwargs: states.pop())

    with pytest.raises(IndexError):
        call_nominatim()

    assert index_mock.called == 4


def test_replication_update_continuous_no_change(monkeypatch, init_status, index_mock):
    states = [nominatim.tools.replication.UpdateState.NO_CHANGES,
              nominatim.tools.replication.UpdateState.UP_TO_DATE]
    monkeypatch.setattr(nominatim.tools.replication, 'update',
                        lambda *args, **kwargs: states.pop())

    sleep_mock = MockParamCapture()
    monkeypatch.setattr(time, 'sleep', sleep_mock)

    with pytest.raises(IndexError):
        call_nominatim()

    assert index_mock.called == 2
    assert sleep_mock.called == 1
    assert sleep_mock.last_args[0] == 60
