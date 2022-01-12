# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for command line interface wrapper.

These tests just check that the various command line parameters route to the
correct functionionality. They use a lot of monkeypatching to avoid executing
the actual functions.
"""
import pytest

import nominatim.indexer.indexer
import nominatim.tools.add_osm_data
import nominatim.tools.freeze


def test_cli_help(cli_call, capsys):
    """ Running nominatim tool without arguments prints help.
    """
    assert cli_call() == 1

    captured = capsys.readouterr()
    assert captured.out.startswith('usage:')


@pytest.mark.parametrize("name,oid", [('file', 'foo.osm'), ('diff', 'foo.osc')])
def test_cli_add_data_file_command(cli_call, mock_func_factory, name, oid):
    mock_run_legacy = mock_func_factory(nominatim.tools.add_osm_data, 'add_data_from_file')
    assert cli_call('add-data', '--' + name, str(oid)) == 0

    assert mock_run_legacy.called == 1


@pytest.mark.parametrize("name,oid", [('node', 12), ('way', 8), ('relation', 32)])
def test_cli_add_data_object_command(cli_call, mock_func_factory, name, oid):
    mock_run_legacy = mock_func_factory(nominatim.tools.add_osm_data, 'add_osm_object')
    assert cli_call('add-data', '--' + name, str(oid)) == 0

    assert mock_run_legacy.called == 1



def test_cli_add_data_tiger_data(cli_call, cli_tokenizer_mock, mock_func_factory):
    mock = mock_func_factory(nominatim.tools.tiger_data, 'add_tiger_data')

    assert cli_call('add-data', '--tiger-data', 'somewhere') == 0

    assert mock.called == 1


def test_cli_serve_command(cli_call, mock_func_factory):
    func = mock_func_factory(nominatim.cli, 'run_php_server')

    cli_call('serve') == 0

    assert func.called == 1


def test_cli_export_command(cli_call, mock_run_legacy):
    assert cli_call('export', '--output-all-postcodes') == 0

    assert mock_run_legacy.called == 1
    assert mock_run_legacy.last_args[0] == 'export.php'


@pytest.mark.parametrize("param,value", [('output-type', 'country'),
                                         ('output-format', 'street;city'),
                                         ('language', 'xf'),
                                         ('restrict-to-country', 'us'),
                                         ('restrict-to-osm-node', '536'),
                                         ('restrict-to-osm-way', '727'),
                                         ('restrict-to-osm-relation', '197532')
                                        ])
def test_export_parameters(src_dir, tmp_path, param, value):
    (tmp_path / 'admin').mkdir()
    (tmp_path / 'admin' / 'export.php').write_text(f"""<?php
        exit(strpos(implode(' ', $_SERVER['argv']), '--{param} {value}') >= 0 ? 0 : 10);
        """)

    assert nominatim.cli.nominatim(module_dir='MODULE NOT AVAILABLE',
                                   osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                   phplib_dir=str(tmp_path),
                                   data_dir=str(src_dir / 'data'),
                                   phpcgi_path='/usr/bin/php-cgi',
                                   sqllib_dir=str(src_dir / 'lib-sql'),
                                   config_dir=str(src_dir / 'settings'),
                                   cli_args=['export', '--' + param, value]) == 0



class TestCliWithDb:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, cli_call, temp_db, cli_tokenizer_mock):
        self.call_nominatim = cli_call
        self.tokenizer_mock = cli_tokenizer_mock


    def test_freeze_command(self, mock_func_factory):
        mock_drop = mock_func_factory(nominatim.tools.freeze, 'drop_update_tables')
        mock_flatnode = mock_func_factory(nominatim.tools.freeze, 'drop_flatnode_file')

        assert self.call_nominatim('freeze') == 0

        assert mock_drop.called == 1
        assert mock_flatnode.called == 1


    @pytest.mark.parametrize("params,do_bnds,do_ranks", [
                              ([], 1, 1),
                              (['--boundaries-only'], 1, 0),
                              (['--no-boundaries'], 0, 1),
                              (['--boundaries-only', '--no-boundaries'], 0, 0)])
    def test_index_command(self, mock_func_factory, table_factory,
                           params, do_bnds, do_ranks):
        table_factory('import_status', 'indexed bool')
        bnd_mock = mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_boundaries')
        rank_mock = mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_by_rank')

        assert self.call_nominatim('index', *params) == 0

        assert bnd_mock.called == do_bnds
        assert rank_mock.called == do_ranks


    def test_special_phrases_wiki_command(self, mock_func_factory):
        func = mock_func_factory(nominatim.clicmd.special_phrases.SPImporter, 'import_phrases')

        self.call_nominatim('special-phrases', '--import-from-wiki', '--no-replace')

        assert func.called == 1


    def test_special_phrases_csv_command(self, src_dir, mock_func_factory):
        func = mock_func_factory(nominatim.clicmd.special_phrases.SPImporter, 'import_phrases')
        testdata = src_dir / 'test' / 'testdb'
        csv_path = str((testdata / 'full_en_phrases_test.csv').resolve())

        self.call_nominatim('special-phrases', '--import-from-csv', csv_path)

        assert func.called == 1


    def test_special_phrases_csv_bad_file(self, src_dir):
        testdata = src_dir / 'something349053905.csv'

        self.call_nominatim('special-phrases', '--import-from-csv',
                            str(testdata.resolve())) == 1
