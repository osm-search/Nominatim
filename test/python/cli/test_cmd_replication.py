# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for replication command of command-line interface wrapper.
"""
import datetime as dt
import time

import pytest

import nominatim.cli
import nominatim.indexer.indexer
import nominatim.tools.replication
import nominatim.tools.refresh
from nominatim.db import status

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
    monkeypatch.setattr(nominatim.tokenizer.factory, 'get_tokenizer_for_db',
                        lambda *args: tok)
    monkeypatch.setattr(nominatim.tokenizer.factory, 'create_tokenizer',
                        lambda *args: tok)

    return tok



@pytest.fixture
def init_status(temp_db_conn, status_table):
    status.set_status(temp_db_conn, date=dt.datetime.now(dt.timezone.utc), seq=1)


@pytest.fixture
def index_mock(mock_func_factory, tokenizer_mock, init_status):
    return mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_full')


@pytest.fixture
def update_mock(mock_func_factory, init_status, tokenizer_mock):
    return mock_func_factory(nominatim.tools.replication, 'update')


class TestCliReplication:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, cli_call, temp_db):
        self.call_nominatim = lambda *args: cli_call('replication', *args)


    @pytest.fixture(autouse=True)
    def setup_update_function(self, monkeypatch):
        def _mock_updates(states):
            monkeypatch.setattr(nominatim.tools.replication, 'update',
                            lambda *args, **kwargs: states.pop())

        self.update_states = _mock_updates


    @pytest.mark.parametrize("params,func", [
                             (('--init',), 'init_replication'),
                             (('--init', '--no-update-functions'), 'init_replication'),
                             (('--check-for-updates',), 'check_for_updates')
                             ])
    def test_replication_command(self, mock_func_factory, params, func):
        func_mock = mock_func_factory(nominatim.tools.replication, func)

        if params == ('--init',):
            umock = mock_func_factory(nominatim.tools.refresh, 'create_functions')

        assert self.call_nominatim(*params) == 0
        assert func_mock.called == 1
        if params == ('--init',):
            assert umock.called == 1


    def test_replication_update_bad_interval(self, monkeypatch):
        monkeypatch.setenv('NOMINATIM_REPLICATION_UPDATE_INTERVAL', 'xx')

        assert self.call_nominatim() == 1


    def test_replication_update_bad_interval_for_geofabrik(self, monkeypatch):
        monkeypatch.setenv('NOMINATIM_REPLICATION_URL',
                           'https://download.geofabrik.de/europe/italy-updates')

        assert self.call_nominatim() == 1


    def test_replication_update_continuous_no_index(self):
        assert self.call_nominatim('--no-index') == 1

    def test_replication_update_once_no_index(self, update_mock):
        assert self.call_nominatim('--once', '--no-index') == 0

        assert str(update_mock.last_args[1]['osm2pgsql']).endswith('OSM2PGSQL NOT AVAILABLE')


    def test_replication_update_custom_osm2pgsql(self, monkeypatch, update_mock):
        monkeypatch.setenv('NOMINATIM_OSM2PGSQL_BINARY', '/secret/osm2pgsql')
        assert self.call_nominatim('--once', '--no-index') == 0

        assert str(update_mock.last_args[1]['osm2pgsql']) == '/secret/osm2pgsql'


    @pytest.mark.parametrize("update_interval", [60, 3600])
    def test_replication_catchup(self, placex_table, monkeypatch, index_mock, update_interval):
        monkeypatch.setenv('NOMINATIM_REPLICATION_UPDATE_INTERVAL', str(update_interval))
        self.update_states([nominatim.tools.replication.UpdateState.NO_CHANGES])

        assert self.call_nominatim('--catch-up') == 0


    def test_replication_update_custom_threads(self, update_mock):
        assert self.call_nominatim('--once', '--no-index', '--threads', '4') == 0

        assert update_mock.last_args[1]['threads'] == 4


    def test_replication_update_continuous(self, index_mock):
        self.update_states([nominatim.tools.replication.UpdateState.UP_TO_DATE,
                            nominatim.tools.replication.UpdateState.UP_TO_DATE])

        with pytest.raises(IndexError):
            self.call_nominatim()

        assert index_mock.called == 2


    def test_replication_update_continuous_no_change(self, mock_func_factory,
                                                     index_mock):
        self.update_states([nominatim.tools.replication.UpdateState.NO_CHANGES,
                            nominatim.tools.replication.UpdateState.UP_TO_DATE])

        sleep_mock = mock_func_factory(time, 'sleep')

        with pytest.raises(IndexError):
            self.call_nominatim()

        assert index_mock.called == 1
        assert sleep_mock.called == 1
        assert sleep_mock.last_args[0] == 60
