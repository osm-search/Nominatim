"""
Tests for command line interface wrapper.
"""
import pytest

import nominatim.cli

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
    def __init__(self):
        self.called = 0
        self.return_value = 0

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

@pytest.fixture
def mock_run_api(monkeypatch):
    mock = MockParamCapture()
    monkeypatch.setattr(nominatim.cli, 'run_api_script', mock)
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
                         (('replication',), 'update'),
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
def test_api_commands_simple(mock_run_api, params):
    assert 0 == call_nominatim(*params)

    assert mock_run_api.called == 1
    assert mock_run_api.last_args[0] == params[0]
