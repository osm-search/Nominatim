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
