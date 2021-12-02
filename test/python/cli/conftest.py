import pytest

import nominatim.cli

class MockParamCapture:
    """ Mock that records the parameters with which a function was called
        as well as the number of calls.
    """
    def __init__(self, retval=0):
        self.called = 0
        self.return_value = retval
        self.last_args = None
        self.last_kwargs = None

    def __call__(self, *args, **kwargs):
        self.called += 1
        self.last_args = args
        self.last_kwargs = kwargs
        return self.return_value


class DummyTokenizer:
    def __init__(self, *args, **kwargs):
        self.update_sql_functions_called = False
        self.finalize_import_called = False
        self.update_statistics_called = False

    def update_sql_functions(self, *args):
        self.update_sql_functions_called = True

    def finalize_import(self, *args):
        self.finalize_import_called = True

    def update_statistics(self):
        self.update_statistics_called = True


@pytest.fixture
def cli_call(src_dir):
    """ Call the nominatim main function with the correct paths set.
        Returns a function that can be called with the desired CLI arguments.
    """
    def _call_nominatim(*args):
        return nominatim.cli.nominatim(module_dir='MODULE NOT AVAILABLE',
                                       osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                       phplib_dir=str(src_dir / 'lib-php'),
                                       data_dir=str(src_dir / 'data'),
                                       phpcgi_path='/usr/bin/php-cgi',
                                       sqllib_dir=str(src_dir / 'lib-sql'),
                                       config_dir=str(src_dir / 'settings'),
                                       cli_args=args)

    return _call_nominatim


@pytest.fixture
def mock_run_legacy(monkeypatch):
    mock = MockParamCapture()
    monkeypatch.setattr(nominatim.cli, 'run_legacy_script', mock)
    return mock


@pytest.fixture
def mock_func_factory(monkeypatch):
    def get_mock(module, func):
        mock = MockParamCapture()
        mock.func_name = func
        monkeypatch.setattr(module, func, mock)
        return mock

    return get_mock


@pytest.fixture
def cli_tokenizer_mock(monkeypatch):
    tok = DummyTokenizer()
    monkeypatch.setattr(nominatim.tokenizer.factory, 'get_tokenizer_for_db',
                        lambda *args: tok)
    monkeypatch.setattr(nominatim.tokenizer.factory, 'create_tokenizer',
                        lambda *args: tok)

    return tok
