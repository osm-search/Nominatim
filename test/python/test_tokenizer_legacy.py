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
def tokenizer_factory(dsn, tmp_path, monkeypatch):

    def _maker():
        return legacy_tokenizer.create(dsn, tmp_path / 'tokenizer')

    return _maker

@pytest.fixture
def tokenizer_setup(tokenizer_factory, test_config, property_table,
                    monkeypatch, sql_preprocessor):
    monkeypatch.setattr(legacy_tokenizer, '_check_module' , lambda m, c: None)
    tok = tokenizer_factory()
    tok.init_new_db(test_config)


def test_init_new(tokenizer_factory, test_config, property_table, monkeypatch,
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


def test_init_module_load_failed(tokenizer_factory, test_config, property_table,
                                 monkeypatch, temp_db_conn):
    tok = tokenizer_factory()

    with pytest.raises(UsageError):
        tok.init_new_db(test_config)


def test_init_module_custom(tokenizer_factory, test_config, property_table,
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
