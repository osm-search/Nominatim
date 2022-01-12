# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for the command line interface wrapper admin subcommand.

These tests just check that the various command line parameters route to the
correct functionionality. They use a lot of monkeypatching to avoid executing
the actual functions.
"""
import pytest

import nominatim.tools.admin
import nominatim.tools.check_database
import nominatim.tools.migration
import nominatim.clicmd.admin


@pytest.mark.parametrize("params", [('--warm', ),
                                    ('--warm', '--reverse-only'),
                                    ('--warm', '--search-only')])
def test_admin_command_legacy(cli_call, mock_func_factory, params):
    mock_run_legacy = mock_func_factory(nominatim.clicmd.admin, 'run_legacy_script')

    assert cli_call('admin', *params) == 0

    assert mock_run_legacy.called == 1


def test_admin_command_check_database(cli_call, mock_func_factory):
    mock = mock_func_factory(nominatim.tools.check_database, 'check_database')

    assert cli_call('admin', '--check-database') == 0
    assert mock.called == 1


def test_admin_migrate(cli_call, mock_func_factory):
    mock = mock_func_factory(nominatim.tools.migration, 'migrate')

    assert cli_call('admin', '--migrate') == 0
    assert mock.called == 1


class TestCliAdminWithDb:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, cli_call, temp_db, cli_tokenizer_mock):
        self.call_nominatim = cli_call
        self.tokenizer_mock = cli_tokenizer_mock


    @pytest.mark.parametrize("func, params", [('analyse_indexing', ('--analyse-indexing', ))])
    def test_analyse_indexing(self, mock_func_factory, func, params):
        mock = mock_func_factory(nominatim.tools.admin, func)

        assert self.call_nominatim('admin', *params) == 0
        assert mock.called == 1
