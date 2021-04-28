"""
Test for legacy tokenizer.
"""
import shutil

import pytest

from nominatim.tokenizer import legacy_tokenizer
from nominatim.db import properties
from nominatim.errors import UsageError

@pytest.fixture
def test_config(def_config, tmp_path):
    def_config.project_dir = tmp_path / 'project'
    def_config.project_dir.mkdir()

    module_dir = tmp_path / 'module_src'
    module_dir.mkdir()
    (module_dir / 'nominatim.so').write_text('TEST nomiantim.so')

    def_config.lib_dir.module = module_dir

    sqldir = tmp_path / 'sql'
    sqldir.mkdir()
    (sqldir / 'tokenizer').mkdir()
    (sqldir / 'tokenizer' / 'legacy_tokenizer.sql').write_text("SELECT 'a'")
    (sqldir / 'words.sql').write_text("SELECT 'a'")
    shutil.copy(str(def_config.lib_dir.sql / 'tokenizer' / 'legacy_tokenizer_tables.sql'),
                str(sqldir / 'tokenizer' / 'legacy_tokenizer_tables.sql'))

    def_config.lib_dir.sql = sqldir
    def_config.lib_dir.data = sqldir

    return def_config


@pytest.fixture
def tokenizer_factory(dsn, tmp_path, monkeypatch, property_table):

    def _maker():
        return legacy_tokenizer.create(dsn, tmp_path / 'tokenizer')

    return _maker

@pytest.fixture
def tokenizer_setup(tokenizer_factory, test_config, monkeypatch, sql_preprocessor):
    monkeypatch.setattr(legacy_tokenizer, '_check_module' , lambda m, c: None)
    tok = tokenizer_factory()
    tok.init_new_db(test_config)


@pytest.fixture
def analyzer(tokenizer_factory, test_config, monkeypatch, sql_preprocessor,
             word_table, temp_db_with_extensions, tmp_path):
    sql = tmp_path / 'sql' / 'tokenizer' / 'legacy_tokenizer.sql'
    sql.write_text("""
        CREATE OR REPLACE FUNCTION getorcreate_housenumber_id(lookup_word TEXT)
          RETURNS INTEGER AS $$ SELECT 342; $$ LANGUAGE SQL;
        """)

    monkeypatch.setattr(legacy_tokenizer, '_check_module' , lambda m, c: None)
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    with tok.name_analyzer() as analyzer:
        yield analyzer


def test_init_new(tokenizer_factory, test_config, monkeypatch,
                  temp_db_conn, sql_preprocessor):
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', 'xxvv')
    monkeypatch.setattr(legacy_tokenizer, '_check_module' , lambda m, c: None)

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_NORMALIZATION) == 'xxvv'

    outfile = test_config.project_dir / 'module' / 'nominatim.so'

    assert outfile.exists()
    assert outfile.read_text() == 'TEST nomiantim.so'
    assert outfile.stat().st_mode == 33261


def test_init_module_load_failed(tokenizer_factory, test_config,
                                 monkeypatch, temp_db_conn):
    tok = tokenizer_factory()

    with pytest.raises(UsageError):
        tok.init_new_db(test_config)


def test_init_module_custom(tokenizer_factory, test_config,
                            monkeypatch, tmp_path, sql_preprocessor):
    module_dir = (tmp_path / 'custom').resolve()
    module_dir.mkdir()
    (module_dir/ 'nominatim.so').write_text('CUSTOM nomiantim.so')

    monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', str(module_dir))
    monkeypatch.setattr(legacy_tokenizer, '_check_module' , lambda m, c: None)

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert not (test_config.project_dir / 'module').exists()


def test_init_from_project(tokenizer_setup, tokenizer_factory):
    tok = tokenizer_factory()

    tok.init_from_project()

    assert tok.normalization is not None


def test_update_sql_functions(sql_preprocessor, temp_db_conn,
                              tokenizer_factory, test_config, table_factory,
                              monkeypatch, temp_db_cursor):
    monkeypatch.setenv('NOMINATIM_MAX_WORD_FREQUENCY', '1133')
    monkeypatch.setattr(legacy_tokenizer, '_check_module' , lambda m, c: None)
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_MAXWORDFREQ) == '1133'

    table_factory('test', 'txt TEXT')

    func_file = test_config.lib_dir.sql / 'tokenizer' / 'legacy_tokenizer.sql'
    func_file.write_text("""INSERT INTO test VALUES ('{{max_word_freq}}'),
                                                   ('{{modulepath}}')""")

    tok.update_sql_functions(test_config)

    test_content = temp_db_cursor.row_set('SELECT * FROM test')
    assert test_content == set((('1133', ), (str(test_config.project_dir / 'module'), )))


def test_migrate_database(tokenizer_factory, test_config, temp_db_conn, monkeypatch):
    monkeypatch.setattr(legacy_tokenizer, '_check_module' , lambda m, c: None)
    tok = tokenizer_factory()
    tok.migrate_database(test_config)

    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_MAXWORDFREQ) is not None
    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_NORMALIZATION) is not None

    outfile = test_config.project_dir / 'module' / 'nominatim.so'

    assert outfile.exists()
    assert outfile.read_text() == 'TEST nomiantim.so'
    assert outfile.stat().st_mode == 33261


def test_normalize(analyzer):
    assert analyzer.normalize('TEsT') == 'test'
