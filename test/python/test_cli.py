"""
Tests for command line interface wrapper.

These tests just check that the various command line parameters route to the
correct functionionality. They use a lot of monkeypatching to avoid executing
the actual functions.
"""
import pytest

import nominatim.db.properties
import nominatim.cli
import nominatim.clicmd.api
import nominatim.clicmd.refresh
import nominatim.clicmd.admin
import nominatim.clicmd.setup
import nominatim.indexer.indexer
import nominatim.tools.admin
import nominatim.tools.add_osm_data
import nominatim.tools.check_database
import nominatim.tools.database_import
import nominatim.tools.country_info
import nominatim.tools.freeze
import nominatim.tools.refresh
import nominatim.tools.postcodes
import nominatim.tokenizer.factory

from mocks import MockParamCapture

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



class TestCli:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, cli_call):
        self.call_nominatim = cli_call


    def test_cli_help(self, capsys):
        """ Running nominatim tool without arguments prints help.
        """
        assert self.call_nominatim() == 1

        captured = capsys.readouterr()
        assert captured.out.startswith('usage:')


    @pytest.mark.parametrize("command,script", [
                             (('export',), 'export')
                             ])
    def test_legacy_commands_simple(self, mock_run_legacy, command, script):
        assert self.call_nominatim(*command) == 0

        assert mock_run_legacy.called == 1
        assert mock_run_legacy.last_args[0] == script + '.php'


    @pytest.mark.parametrize("params", [('--warm', ),
                                        ('--warm', '--reverse-only'),
                                        ('--warm', '--search-only')])
    def test_admin_command_legacy(self, mock_func_factory, params):
        mock_run_legacy = mock_func_factory(nominatim.clicmd.admin, 'run_legacy_script')

        assert self.call_nominatim('admin', *params) == 0

        assert mock_run_legacy.called == 1


    def test_admin_command_check_database(self, mock_func_factory):
        mock = mock_func_factory(nominatim.tools.check_database, 'check_database')

        assert self.call_nominatim('admin', '--check-database') == 0
        assert mock.called == 1


    @pytest.mark.parametrize("name,oid", [('file', 'foo.osm'), ('diff', 'foo.osc')])
    def test_add_data_file_command(self, mock_func_factory, name, oid):
        mock_run_legacy = mock_func_factory(nominatim.tools.add_osm_data, 'add_data_from_file')
        assert self.call_nominatim('add-data', '--' + name, str(oid)) == 0

        assert mock_run_legacy.called == 1


    @pytest.mark.parametrize("name,oid", [('node', 12), ('way', 8), ('relation', 32)])
    def test_add_data_object_command(self, mock_func_factory, name, oid):
        mock_run_legacy = mock_func_factory(nominatim.tools.add_osm_data, 'add_osm_object')
        assert self.call_nominatim('add-data', '--' + name, str(oid)) == 0

        assert mock_run_legacy.called == 1


    def test_serve_command(self, mock_func_factory):
        func = mock_func_factory(nominatim.cli, 'run_php_server')

        self.call_nominatim('serve')

        assert func.called == 1


    @pytest.mark.parametrize("params", [('search', '--query', 'new'),
                                        ('reverse', '--lat', '0', '--lon', '0'),
                                        ('lookup', '--id', 'N1'),
                                        ('details', '--node', '1'),
                                        ('details', '--way', '1'),
                                        ('details', '--relation', '1'),
                                        ('details', '--place_id', '10001'),
                                        ('status',)])
    def test_api_commands_simple(self, mock_func_factory, params):
        mock_run_api = mock_func_factory(nominatim.clicmd.api, 'run_api_script')

        assert self.call_nominatim(*params) == 0

        assert mock_run_api.called == 1
        assert mock_run_api.last_args[0] == params[0]



class TestCliWithDb:

    @pytest.fixture(autouse=True)
    def setup_cli_call(self, cli_call, temp_db):
        self.call_nominatim = cli_call


    @pytest.fixture(autouse=True)
    def setup_tokenizer_mock(self, monkeypatch):
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


        tok = DummyTokenizer()
        monkeypatch.setattr(nominatim.tokenizer.factory, 'get_tokenizer_for_db',
                            lambda *args: tok)
        monkeypatch.setattr(nominatim.tokenizer.factory, 'create_tokenizer',
                            lambda *args: tok)

        self.tokenizer_mock = tok


    def test_import_missing_file(self):
        assert self.call_nominatim('import', '--osm-file', 'sfsafegwedgw.reh.erh') == 1


    def test_import_bad_file(self):
        assert self.call_nominatim('import', '--osm-file', '.') == 1


    def test_import_full(self, mock_func_factory):
        mocks = [
            mock_func_factory(nominatim.tools.database_import, 'setup_database_skeleton'),
            mock_func_factory(nominatim.tools.country_info, 'setup_country_tables'),
            mock_func_factory(nominatim.tools.database_import, 'import_osm_data'),
            mock_func_factory(nominatim.tools.refresh, 'import_wikipedia_articles'),
            mock_func_factory(nominatim.tools.database_import, 'truncate_data_tables'),
            mock_func_factory(nominatim.tools.database_import, 'load_data'),
            mock_func_factory(nominatim.tools.database_import, 'create_tables'),
            mock_func_factory(nominatim.tools.database_import, 'create_table_triggers'),
            mock_func_factory(nominatim.tools.database_import, 'create_partition_tables'),
            mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim.tools.country_info, 'create_country_names'),
            mock_func_factory(nominatim.tools.refresh, 'load_address_levels_from_file'),
            mock_func_factory(nominatim.tools.postcodes, 'update_postcodes'),
            mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_full'),
            mock_func_factory(nominatim.tools.refresh, 'setup_website'),
            mock_func_factory(nominatim.db.properties, 'set_property')
        ]

        cf_mock = mock_func_factory(nominatim.tools.refresh, 'create_functions')

        assert self.call_nominatim('import', '--osm-file', __file__) == 0
        assert self.tokenizer_mock.finalize_import_called

        assert cf_mock.called > 1

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)


    def test_import_continue_load_data(self, mock_func_factory):
        mocks = [
            mock_func_factory(nominatim.tools.database_import, 'truncate_data_tables'),
            mock_func_factory(nominatim.tools.database_import, 'load_data'),
            mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim.tools.country_info, 'create_country_names'),
            mock_func_factory(nominatim.tools.postcodes, 'update_postcodes'),
            mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_full'),
            mock_func_factory(nominatim.tools.refresh, 'setup_website'),
            mock_func_factory(nominatim.db.properties, 'set_property')
        ]

        assert self.call_nominatim('import', '--continue', 'load-data') == 0
        assert self.tokenizer_mock.finalize_import_called

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)


    def test_import_continue_indexing(self, mock_func_factory, placex_table,
                                      temp_db_conn):
        mocks = [
            mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim.tools.country_info, 'create_country_names'),
            mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_full'),
            mock_func_factory(nominatim.tools.refresh, 'setup_website'),
            mock_func_factory(nominatim.db.properties, 'set_property')
        ]

        assert self.call_nominatim('import', '--continue', 'indexing') == 0

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)

        assert temp_db_conn.index_exists('idx_placex_pendingsector')

        # Calling it again still works for the index
        assert self.call_nominatim('import', '--continue', 'indexing') == 0
        assert temp_db_conn.index_exists('idx_placex_pendingsector')


    def test_import_continue_postprocess(self, mock_func_factory):
        mocks = [
            mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
            mock_func_factory(nominatim.tools.country_info, 'create_country_names'),
            mock_func_factory(nominatim.tools.refresh, 'setup_website'),
            mock_func_factory(nominatim.db.properties, 'set_property')
        ]

        assert self.call_nominatim('import', '--continue', 'db-postprocess') == 0

        assert self.tokenizer_mock.finalize_import_called

        for mock in mocks:
            assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)


    def test_freeze_command(self, mock_func_factory):
        mock_drop = mock_func_factory(nominatim.tools.freeze, 'drop_update_tables')
        mock_flatnode = mock_func_factory(nominatim.tools.freeze, 'drop_flatnode_file')

        assert self.call_nominatim('freeze') == 0

        assert mock_drop.called == 1
        assert mock_flatnode.called == 1



    @pytest.mark.parametrize("func, params", [('analyse_indexing', ('--analyse-indexing', ))])
    def test_admin_command_tool(self, mock_func_factory, func, params):
        mock = mock_func_factory(nominatim.tools.admin, func)

        assert self.call_nominatim('admin', *params) == 0
        assert mock.called == 1


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

    @pytest.mark.parametrize("no_replace", [(True), (False)])
    def test_special_phrases_wiki_command(self, mock_func_factory, no_replace):
        func = mock_func_factory(nominatim.clicmd.special_phrases.SPImporter, 'import_phrases')

        if no_replace:
            self.call_nominatim('special-phrases', '--import-from-wiki', '--no-replace')
        else:
            self.call_nominatim('special-phrases', '--import-from-wiki')

        assert func.called == 1

    @pytest.mark.parametrize("no_replace", [(True), (False)])
    def test_special_phrases_csv_command(self, src_dir, mock_func_factory, no_replace):
        func = mock_func_factory(nominatim.clicmd.special_phrases.SPImporter, 'import_phrases')
        testdata = src_dir / 'test' / 'testdb'
        csv_path = str((testdata / 'full_en_phrases_test.csv').resolve())

        if no_replace:
            self.call_nominatim('special-phrases', '--import-from-csv', csv_path, '--no-replace')
        else:
            self.call_nominatim('special-phrases', '--import-from-csv', csv_path)

        assert func.called == 1

    @pytest.mark.parametrize("command,func", [
                             ('address-levels', 'load_address_levels_from_file'),
                             ('wiki-data', 'import_wikipedia_articles'),
                             ('importance', 'recompute_importance'),
                             ('website', 'setup_website'),
                             ])
    def test_refresh_command(self, mock_func_factory, command, func):
        func_mock = mock_func_factory(nominatim.tools.refresh, func)

        assert self.call_nominatim('refresh', '--' + command) == 0
        assert func_mock.called == 1


    def test_refresh_word_count(self):
        assert self.call_nominatim('refresh', '--word-count') == 0
        assert self.tokenizer_mock.update_statistics_called


    def test_refresh_postcodes(self, mock_func_factory, place_table):
        func_mock = mock_func_factory(nominatim.tools.postcodes, 'update_postcodes')
        idx_mock = mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_postcodes')

        assert self.call_nominatim('refresh', '--postcodes') == 0
        assert func_mock.called == 1
        assert idx_mock.called == 1

    def test_refresh_create_functions(self, mock_func_factory):
        func_mock = mock_func_factory(nominatim.tools.refresh, 'create_functions')

        assert self.call_nominatim('refresh', '--functions') == 0
        assert func_mock.called == 1
        assert self.tokenizer_mock.update_sql_functions_called


    def test_refresh_importance_computed_after_wiki_import(self, monkeypatch):
        calls = []
        monkeypatch.setattr(nominatim.tools.refresh, 'import_wikipedia_articles',
                            lambda *args, **kwargs: calls.append('import') or 0)
        monkeypatch.setattr(nominatim.tools.refresh, 'recompute_importance',
                            lambda *args, **kwargs: calls.append('update'))

        assert self.call_nominatim('refresh', '--importance', '--wiki-data') == 0

        assert calls == ['import', 'update']
