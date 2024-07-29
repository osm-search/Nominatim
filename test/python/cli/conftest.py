# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
import pytest

import nominatim_db.cli

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


class AsyncMockParamCapture:
    """ Mock that records the parameters with which a function was called
        as well as the number of calls.
    """
    def __init__(self, retval=0):
        self.called = 0
        self.return_value = retval
        self.last_args = None
        self.last_kwargs = None

    async def __call__(self, *args, **kwargs):
        self.called += 1
        self.last_args = args
        self.last_kwargs = kwargs
        return self.return_value


class DummyTokenizer:
    def __init__(self, *args, **kwargs):
        self.update_sql_functions_called = False
        self.finalize_import_called = False
        self.update_statistics_called = False
        self.update_word_tokens_called = False

    def update_sql_functions(self, *args, **kwargs):
        self.update_sql_functions_called = True

    def finalize_import(self, *args, **kwargs):
        self.finalize_import_called = True

    def update_statistics(self, *args, **kwargs):
        self.update_statistics_called = True

    def update_word_tokens(self, *args, **kwargs):
        self.update_word_tokens_called = True


@pytest.fixture
def cli_call():
    """ Call the nominatim main function with the correct paths set.
        Returns a function that can be called with the desired CLI arguments.
    """
    def _call_nominatim(*args):
        return nominatim_db.cli.nominatim(module_dir='MODULE NOT AVAILABLE',
                                          osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                          cli_args=args)

    return _call_nominatim


@pytest.fixture
def mock_func_factory(monkeypatch):
    def get_mock(module, func):
        mock = MockParamCapture()
        mock.func_name = func
        monkeypatch.setattr(module, func, mock)
        return mock

    return get_mock


@pytest.fixture
def async_mock_func_factory(monkeypatch):
    def get_mock(module, func):
        mock = AsyncMockParamCapture()
        mock.func_name = func
        monkeypatch.setattr(module, func, mock)
        return mock

    return get_mock


@pytest.fixture
def cli_tokenizer_mock(monkeypatch):
    tok = DummyTokenizer()
    monkeypatch.setattr(nominatim_db.tokenizer.factory, 'get_tokenizer_for_db',
                        lambda *args: tok)
    monkeypatch.setattr(nominatim_db.tokenizer.factory, 'create_tokenizer',
                        lambda *args: tok)

    return tok
