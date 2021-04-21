"""
Test for legacy tokenizer.
"""
import pytest

from nominatim.tokenizer import legacy_tokenizer
from nominatim.db import properties

@pytest.fixture
def tokenizer(dsn, tmp_path, def_config, property_table):
    tok = legacy_tokenizer.create(dsn, tmp_path)
    tok.init_new_db(def_config)

    return tok

def test_init_new(dsn, tmp_path, def_config, property_table, monkeypatch, temp_db_conn):
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', 'xxvv')

    tok = legacy_tokenizer.create(dsn, tmp_path)
    tok.init_new_db(def_config)

    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_NORMALIZATION) == 'xxvv'


def test_init_from_project(tokenizer):
    tokenizer.init_from_project()

    assert tokenizer.normalization is not None
