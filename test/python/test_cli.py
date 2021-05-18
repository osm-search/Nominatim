"""
Tests for command line interface wrapper.

These tests just check that the various command line parameters route to the
correct functionionality. They use a lot of monkeypatching to avoid executing
the actual functions.
"""
from pathlib import Path

import pytest

import nominatim.db.properties
import nominatim.cli
import nominatim.clicmd.api
import nominatim.clicmd.refresh
import nominatim.clicmd.admin
import nominatim.clicmd.setup
import nominatim.indexer.indexer
import nominatim.tools.admin
import nominatim.tools.check_database
import nominatim.tools.database_import
import nominatim.tools.freeze
import nominatim.tools.refresh
import nominatim.tools.postcodes
import nominatim.tokenizer.factory

from mocks import MockParamCapture

SRC_DIR = (Path(__file__) / '..' / '..' / '..').resolve()

def call_nominatim(*args):
    return nominatim.cli.nominatim(module_dir='build/module',
                                   osm2pgsql_path='build/osm2pgsql/osm2pgsql',
                                   phplib_dir=str(SRC_DIR / 'lib-php'),
                                   data_dir=str(SRC_DIR / 'data'),
                                   phpcgi_path='/usr/bin/php-cgi',
                                   sqllib_dir=str(SRC_DIR / 'lib-sql'),
                                   config_dir=str(SRC_DIR / 'settings'),
                                   cli_args=args)


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
    monkeypatch.setattr(nominatim.tokenizer.factory, 'get_tokenizer_for_db' ,
                        lambda *args: tok)
    monkeypatch.setattr(nominatim.tokenizer.factory, 'create_tokenizer' ,
                        lambda *args: tok)

    return tok


def test_cli_help(capsys):
    """ Running nominatim tool without arguments prints help.
    """
    assert 1 == call_nominatim()

    captured = capsys.readouterr()
    assert captured.out.startswith('usage:')


@pytest.mark.parametrize("command,script", [
                         (('add-data', '--file', 'foo.osm'), 'update'),
                         (('export',), 'export')
                         ])
def test_legacy_commands_simple(mock_run_legacy, command, script):
    assert 0 == call_nominatim(*command)

    assert mock_run_legacy.called == 1
    assert mock_run_legacy.last_args[0] == script + '.php'


def test_import_missing_file(temp_db):
    assert 1 == call_nominatim('import', '--osm-file', 'sfsafegweweggdgw.reh.erh')


def test_import_bad_file(temp_db):
    assert 1 == call_nominatim('import', '--osm-file', '.')


def test_import_full(temp_db, mock_func_factory, tokenizer_mock):
    mocks = [
        mock_func_factory(nominatim.tools.database_import, 'setup_database_skeleton'),
        mock_func_factory(nominatim.tools.database_import, 'import_osm_data'),
        mock_func_factory(nominatim.tools.refresh, 'import_wikipedia_articles'),
        mock_func_factory(nominatim.tools.database_import, 'truncate_data_tables'),
        mock_func_factory(nominatim.tools.database_import, 'load_data'),
        mock_func_factory(nominatim.tools.database_import, 'create_tables'),
        mock_func_factory(nominatim.tools.database_import, 'create_table_triggers'),
        mock_func_factory(nominatim.tools.database_import, 'create_partition_tables'),
        mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
        mock_func_factory(nominatim.tools.database_import, 'create_country_names'),
        mock_func_factory(nominatim.tools.refresh, 'load_address_levels_from_file'),
        mock_func_factory(nominatim.tools.postcodes, 'update_postcodes'),
        mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_full'),
        mock_func_factory(nominatim.tools.refresh, 'setup_website'),
        mock_func_factory(nominatim.db.properties, 'set_property')
    ]

    cf_mock = mock_func_factory(nominatim.tools.refresh, 'create_functions')

    assert 0 == call_nominatim('import', '--osm-file', __file__)
    assert tokenizer_mock.finalize_import_called

    assert cf_mock.called > 1

    for mock in mocks:
        assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)


def test_import_continue_load_data(temp_db, mock_func_factory, tokenizer_mock):
    mocks = [
        mock_func_factory(nominatim.tools.database_import, 'truncate_data_tables'),
        mock_func_factory(nominatim.tools.database_import, 'load_data'),
        mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
        mock_func_factory(nominatim.tools.database_import, 'create_country_names'),
        mock_func_factory(nominatim.tools.postcodes, 'update_postcodes'),
        mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_full'),
        mock_func_factory(nominatim.tools.refresh, 'setup_website'),
        mock_func_factory(nominatim.db.properties, 'set_property')
    ]

    assert 0 == call_nominatim('import', '--continue', 'load-data')
    assert tokenizer_mock.finalize_import_called

    for mock in mocks:
        assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)


def test_import_continue_indexing(temp_db, mock_func_factory, placex_table,
                                  temp_db_conn, tokenizer_mock):
    mocks = [
        mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
        mock_func_factory(nominatim.tools.database_import, 'create_country_names'),
        mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_full'),
        mock_func_factory(nominatim.tools.refresh, 'setup_website'),
        mock_func_factory(nominatim.db.properties, 'set_property')
    ]

    assert 0 == call_nominatim('import', '--continue', 'indexing')

    for mock in mocks:
        assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)

    assert temp_db_conn.index_exists('idx_placex_pendingsector')

    # Calling it again still works for the index
    assert 0 == call_nominatim('import', '--continue', 'indexing')
    assert temp_db_conn.index_exists('idx_placex_pendingsector')


def test_import_continue_postprocess(temp_db, mock_func_factory, tokenizer_mock):
    mocks = [
        mock_func_factory(nominatim.tools.database_import, 'create_search_indices'),
        mock_func_factory(nominatim.tools.database_import, 'create_country_names'),
        mock_func_factory(nominatim.tools.refresh, 'setup_website'),
        mock_func_factory(nominatim.db.properties, 'set_property')
    ]

    assert 0 == call_nominatim('import', '--continue', 'db-postprocess')

    assert tokenizer_mock.finalize_import_called

    for mock in mocks:
        assert mock.called == 1, "Mock '{}' not called".format(mock.func_name)


def test_freeze_command(mock_func_factory, temp_db):
    mock_drop = mock_func_factory(nominatim.tools.freeze, 'drop_update_tables')
    mock_flatnode = mock_func_factory(nominatim.tools.freeze, 'drop_flatnode_file')

    assert 0 == call_nominatim('freeze')

    assert mock_drop.called == 1
    assert mock_flatnode.called == 1


@pytest.mark.parametrize("params", [('--warm', ),
                                    ('--warm', '--reverse-only'),
                                    ('--warm', '--search-only')])
def test_admin_command_legacy(mock_func_factory, params):
    mock_run_legacy = mock_func_factory(nominatim.clicmd.admin, 'run_legacy_script')

    assert 0 == call_nominatim('admin', *params)

    assert mock_run_legacy.called == 1


@pytest.mark.parametrize("func, params", [('analyse_indexing', ('--analyse-indexing', ))])
def test_admin_command_tool(temp_db, mock_func_factory, func, params):
    mock = mock_func_factory(nominatim.tools.admin, func)

    assert 0 == call_nominatim('admin', *params)
    assert mock.called == 1


def test_admin_command_check_database(mock_func_factory):
    mock = mock_func_factory(nominatim.tools.check_database, 'check_database')

    assert 0 == call_nominatim('admin', '--check-database')
    assert mock.called == 1


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
def test_index_command(mock_func_factory, temp_db_cursor, tokenizer_mock,
                       params, do_bnds, do_ranks):
    temp_db_cursor.execute("CREATE TABLE import_status (indexed bool)")
    bnd_mock = mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_boundaries')
    rank_mock = mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_by_rank')

    assert 0 == call_nominatim('index', *params)

    assert bnd_mock.called == do_bnds
    assert rank_mock.called == do_ranks

@pytest.mark.parametrize("no_replace", [(True), (False)])
def test_special_phrases_wiki_command(temp_db, mock_func_factory, tokenizer_mock, no_replace):
    func = mock_func_factory(nominatim.clicmd.special_phrases.SPImporter, 'import_phrases')

    if no_replace:
        call_nominatim('special-phrases', '--import-from-wiki', '--no-replace')
    else:
        call_nominatim('special-phrases', '--import-from-wiki')

    assert func.called == 1

@pytest.mark.parametrize("no_replace", [(True), (False)])
def test_special_phrases_csv_command(temp_db, mock_func_factory, tokenizer_mock, no_replace):
    func = mock_func_factory(nominatim.clicmd.special_phrases.SPImporter, 'import_phrases')
    testdata = SRC_DIR / 'test' / 'testdb'
    csv_path = str((testdata / 'full_en_phrases_test.csv').resolve())

    if no_replace:
        call_nominatim('special-phrases', '--import-from-csv', csv_path, '--no-replace')
    else:
        call_nominatim('special-phrases', '--import-from-csv', csv_path)

    assert func.called == 1

@pytest.mark.parametrize("command,func", [
                         ('word-counts', 'recompute_word_counts'),
                         ('address-levels', 'load_address_levels_from_file'),
                         ('wiki-data', 'import_wikipedia_articles'),
                         ('importance', 'recompute_importance'),
                         ('website', 'setup_website'),
                         ])
def test_refresh_command(mock_func_factory, temp_db, command, func, tokenizer_mock):
    func_mock = mock_func_factory(nominatim.tools.refresh, func)

    assert 0 == call_nominatim('refresh', '--' + command)
    assert func_mock.called == 1


def test_refresh_postcodes(mock_func_factory, temp_db, tokenizer_mock):
    func_mock = mock_func_factory(nominatim.tools.postcodes, 'update_postcodes')
    idx_mock = mock_func_factory(nominatim.indexer.indexer.Indexer, 'index_postcodes')

    assert 0 == call_nominatim('refresh', '--postcodes')
    assert func_mock.called == 1

def test_refresh_create_functions(mock_func_factory, temp_db, tokenizer_mock):
    func_mock = mock_func_factory(nominatim.tools.refresh, 'create_functions')

    assert 0 == call_nominatim('refresh', '--functions')
    assert func_mock.called == 1
    assert tokenizer_mock.update_sql_functions_called


def test_refresh_importance_computed_after_wiki_import(monkeypatch, temp_db, tokenizer_mock):
    calls = []
    monkeypatch.setattr(nominatim.tools.refresh, 'import_wikipedia_articles',
                        lambda *args, **kwargs: calls.append('import') or 0)
    monkeypatch.setattr(nominatim.tools.refresh, 'recompute_importance',
                        lambda *args, **kwargs: calls.append('update'))

    assert 0 == call_nominatim('refresh', '--importance', '--wiki-data')

    assert calls == ['import', 'update']


def test_serve_command(mock_func_factory):
    func = mock_func_factory(nominatim.cli, 'run_php_server')

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
def test_api_commands_simple(mock_func_factory, params):
    mock_run_api = mock_func_factory(nominatim.clicmd.api, 'run_api_script')

    assert 0 == call_nominatim(*params)

    assert mock_run_api.called == 1
    assert mock_run_api.last_args[0] == params[0]
