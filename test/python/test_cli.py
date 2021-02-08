"""
Tests for command line interface wrapper.

These tests just check that the various command line parameters route to the
correct functionionality. They use a lot of monkeypatching to avoid executing
the actual functions.
"""
import datetime as dt
import psycopg2
import pytest
import time

import nominatim.cli
import nominatim.clicmd.api
import nominatim.clicmd.refresh
import nominatim.indexer.indexer
import nominatim.tools.refresh
import nominatim.tools.replication
from nominatim.errors import UsageError
from nominatim.db import status

def call_nominatim(*args):
    return nominatim.cli.nominatim(module_dir='build/module',
                                   osm2pgsql_path='build/osm2pgsql/osm2pgsql',
                                   phplib_dir='lib',
                                   data_dir='.',
                                   phpcgi_path='/usr/bin/php-cgi',
                                   cli_args=args)

class MockParamCapture:
    """ Mock that records the parameters with which a function was called
        as well as the number of calls.
    """
    def __init__(self, retval=0):
        self.called = 0
        self.return_value = retval

    def __call__(self, *args, **kwargs):
        self.called += 1
        self.last_args = args
        self.last_kwargs = kwargs
        return self.return_value

@pytest.fixture
def mock_run_legacy(monkeypatch):
    mock = MockParamCapture()
    monkeypatch.setattr(nominatim.cli, 'run_legacy_script', mock)
    return mock


def test_cli_help(capsys):
    """ Running nominatim tool without arguments prints help.
    """
    assert 1 == call_nominatim()

    captured = capsys.readouterr()
    assert captured.out.startswith('usage:')


@pytest.mark.parametrize("command,script", [
                         (('import', '--continue', 'load-data'), 'setup'),
                         (('freeze',), 'setup'),
                         (('special-phrases',), 'specialphrases'),
                         (('add-data', '--tiger-data', 'tiger'), 'setup'),
                         (('add-data', '--file', 'foo.osm'), 'update'),
                         (('check-database',), 'check_import_finished'),
                         (('warm',), 'warm'),
                         (('export',), 'export')
                         ])
def test_legacy_commands_simple(mock_run_legacy, command, script):
    assert 0 == call_nominatim(*command)

    assert mock_run_legacy.called == 1
    assert mock_run_legacy.last_args[0] == script + '.php'


@pytest.mark.parametrize("name,oid", [('file', 'foo.osm'), ('diff', 'foo.osc'),
                                      ('node', 12), ('way', 8), ('relation', 32)])
def test_add_data_command(mock_run_legacy, name, oid):
    assert 0 == call_nominatim('add-data', '--' + name, str(oid))

    assert mock_run_legacy.called == 1
    assert mock_run_legacy.last_args == ('update.php', '--import-' + name, oid)


@pytest.mark.parametrize("params,do_bnds,do_ranks", [
                          ([], 1, 1),
                          (['--boundaries-only'], 1, 0),
                          (['--no-boundaries'], 0, 1),
                          (['--boundaries-only', '--no-boundaries'], 0, 0)])
def test_index_command(monkeypatch, temp_db_cursor, params, do_bnds, do_ranks):
    temp_db_cursor.execute("CREATE TABLE import_status (indexed bool)")
    bnd_mock = MockParamCapture()
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_boundaries', bnd_mock)
    rank_mock = MockParamCapture()
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_by_rank', rank_mock)

    assert 0 == call_nominatim('index', *params)

    assert bnd_mock.called == do_bnds
    assert rank_mock.called == do_ranks


@pytest.mark.parametrize("command,params", [
                         ('wiki-data', ('setup.php', '--import-wikipedia-articles')),
                         ('importance', ('update.php', '--recompute-importance')),
                         ('website', ('setup.php', '--setup-website')),
                         ])
def test_refresh_legacy_command(monkeypatch, temp_db, command, params):
    mock_run_legacy = MockParamCapture()
    monkeypatch.setattr(nominatim.clicmd.refresh, 'run_legacy_script', mock_run_legacy)

    assert 0 == call_nominatim('refresh', '--' + command)

    assert mock_run_legacy.called == 1
    assert len(mock_run_legacy.last_args) >= len(params)
    assert mock_run_legacy.last_args[:len(params)] == params

@pytest.mark.parametrize("command,func", [
                         ('postcodes', 'update_postcodes'),
                         ('word-counts', 'recompute_word_counts'),
                         ('address-levels', 'load_address_levels_from_file'),
                         ('functions', 'create_functions'),
                         ])
def test_refresh_command(monkeypatch, temp_db, command, func):
    func_mock = MockParamCapture()
    monkeypatch.setattr(nominatim.tools.refresh, func, func_mock)

    assert 0 == call_nominatim('refresh', '--' + command)
    assert func_mock.called == 1


def test_refresh_importance_computed_after_wiki_import(monkeypatch, temp_db):
    mock_run_legacy = MockParamCapture()
    monkeypatch.setattr(nominatim.clicmd.refresh, 'run_legacy_script', mock_run_legacy)

    assert 0 == call_nominatim('refresh', '--importance', '--wiki-data')

    assert mock_run_legacy.called == 2
    assert mock_run_legacy.last_args == ('update.php', '--recompute-importance')


@pytest.mark.parametrize("params,func", [
                         (('--init', '--no-update-functions'), 'init_replication'),
                         (('--check-for-updates',), 'check_for_updates')
                         ])
def test_replication_command(monkeypatch, temp_db, params, func):
    func_mock = MockParamCapture()
    monkeypatch.setattr(nominatim.tools.replication, func, func_mock)

    assert 0 == call_nominatim('replication', *params)
    assert func_mock.called == 1


def test_replication_update_bad_interval(monkeypatch, temp_db):
    monkeypatch.setenv('NOMINATIM_REPLICATION_UPDATE_INTERVAL', 'xx')

    assert call_nominatim('replication') == 1


def test_replication_update_bad_interval_for_geofabrik(monkeypatch, temp_db):
    monkeypatch.setenv('NOMINATIM_REPLICATION_URL',
                       'https://download.geofabrik.de/europe/ireland-and-northern-ireland-updates')

    assert call_nominatim('replication') == 1


@pytest.mark.parametrize("state, retval", [
                         (nominatim.tools.replication.UpdateState.UP_TO_DATE, 0),
                         (nominatim.tools.replication.UpdateState.NO_CHANGES, 3)
                         ])
def test_replication_update_once_no_index(monkeypatch, temp_db, temp_db_conn,
                                          status_table, state, retval):
    status.set_status(temp_db_conn, date=dt.datetime.now(dt.timezone.utc), seq=1)
    func_mock = MockParamCapture(retval=state)
    monkeypatch.setattr(nominatim.tools.replication, 'update', func_mock)

    assert retval == call_nominatim('replication', '--once', '--no-index')


def test_replication_update_continuous(monkeypatch, temp_db_conn, status_table):
    status.set_status(temp_db_conn, date=dt.datetime.now(dt.timezone.utc), seq=1)
    states = [nominatim.tools.replication.UpdateState.UP_TO_DATE,
              nominatim.tools.replication.UpdateState.UP_TO_DATE]
    monkeypatch.setattr(nominatim.tools.replication, 'update',
                        lambda *args, **kwargs: states.pop())

    index_mock = MockParamCapture()
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_boundaries', index_mock)
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_by_rank', index_mock)

    with pytest.raises(IndexError):
        call_nominatim('replication')

    assert index_mock.called == 4


def test_replication_update_continuous_no_change(monkeypatch, temp_db_conn, status_table):
    status.set_status(temp_db_conn, date=dt.datetime.now(dt.timezone.utc), seq=1)
    states = [nominatim.tools.replication.UpdateState.NO_CHANGES,
              nominatim.tools.replication.UpdateState.UP_TO_DATE]
    monkeypatch.setattr(nominatim.tools.replication, 'update',
                        lambda *args, **kwargs: states.pop())

    index_mock = MockParamCapture()
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_boundaries', index_mock)
    monkeypatch.setattr(nominatim.indexer.indexer.Indexer, 'index_by_rank', index_mock)

    sleep_mock = MockParamCapture()
    monkeypatch.setattr(time, 'sleep', sleep_mock)

    with pytest.raises(IndexError):
        call_nominatim('replication')

    assert index_mock.called == 2
    assert sleep_mock.called == 1
    assert sleep_mock.last_args[0] == 60


def test_serve_command(monkeypatch):
    func = MockParamCapture()
    monkeypatch.setattr(nominatim.cli, 'run_php_server', func)

    call_nominatim('serve')

    assert func.called == 1

@pytest.mark.parametrize("params", [
                         ('search', '--query', 'new'),
                         ('reverse', '--lat', '0', '--lon', '0'),
                         ('lookup', '--id', 'N1'),
                         ('details', '--node', '1'),
                         ('details', '--way', '1'),
                         ('details', '--relation', '1'),
                         ('details', '--place_id', '10001'),
                         ('status',)
                         ])
def test_api_commands_simple(monkeypatch, params):
    mock_run_api = MockParamCapture()
    monkeypatch.setattr(nominatim.clicmd.api, 'run_api_script', mock_run_api)

    assert 0 == call_nominatim(*params)

    assert mock_run_api.called == 1
    assert mock_run_api.last_args[0] == params[0]
