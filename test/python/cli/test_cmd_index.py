# SPDX-License-Identifier: GPL-2.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for index command of the command-line interface wrapper.
"""
import pytest

import nominatim_db.indexer.indexer


class TestCliIndexWithDb:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, cli_call, cli_tokenizer_mock):
        self.call_nominatim = cli_call
        self.tokenizer_mock = cli_tokenizer_mock

    def test_index_empty_subset(self, monkeypatch, async_mock_func_factory, placex_row):
        placex_row(rank_address=1, indexed_status=1)
        placex_row(rank_address=20, indexed_status=1)

        mocks = [
            async_mock_func_factory(nominatim_db.indexer.indexer.Indexer, 'index_boundaries'),
            async_mock_func_factory(nominatim_db.indexer.indexer.Indexer, 'index_by_rank'),
            async_mock_func_factory(nominatim_db.indexer.indexer.Indexer, 'index_postcodes'),
        ]

        def _reject_repeat_call(*args, **kwargs):
            assert False, "Did not expect multiple Indexer.has_pending invocations"

        has_pending_calls = [nominatim_db.indexer.indexer.Indexer.has_pending, _reject_repeat_call]
        monkeypatch.setattr(nominatim_db.indexer.indexer.Indexer, 'has_pending',
                            lambda *args, **kwargs: has_pending_calls.pop(0)(*args, **kwargs))

        assert self.call_nominatim('index', '--minrank', '5', '--maxrank', '10') == 0

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)
