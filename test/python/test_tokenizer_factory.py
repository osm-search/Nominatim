"""
Tests for creating new tokenizers.
"""
import pytest

from nominatim.db import properties
from nominatim.tokenizer import factory
from nominatim.errors import UsageError
from dummy_tokenizer import DummyTokenizer

@pytest.fixture
def test_config(def_config, tmp_path, property_table, tokenizer_mock):
    def_config.project_dir = tmp_path
    return def_config


def test_setup_dummy_tokenizer(temp_db_conn, test_config):
    tokenizer = factory.create_tokenizer(test_config)

    assert isinstance(tokenizer, DummyTokenizer)
    assert tokenizer.init_state == "new"
    assert (test_config.project_dir / 'tokenizer').is_dir()

    assert properties.get_property(temp_db_conn, 'tokenizer') == 'dummy'


def test_setup_tokenizer_dir_exists(test_config):
    (test_config.project_dir / 'tokenizer').mkdir()

    tokenizer = factory.create_tokenizer(test_config)

    assert isinstance(tokenizer, DummyTokenizer)
    assert tokenizer.init_state == "new"


def test_setup_tokenizer_dir_failure(test_config):
    (test_config.project_dir / 'tokenizer').write_text("foo")

    with pytest.raises(UsageError):
        factory.create_tokenizer(test_config)


def test_setup_bad_tokenizer_name(def_config, tmp_path, monkeypatch):
    def_config.project_dir = tmp_path
    monkeypatch.setenv('NOMINATIM_TOKENIZER', 'dummy')

    with pytest.raises(UsageError):
        factory.create_tokenizer(def_config)


def test_load_tokenizer(test_config):
    factory.create_tokenizer(test_config)

    tokenizer = factory.get_tokenizer_for_db(test_config)

    assert isinstance(tokenizer, DummyTokenizer)
    assert tokenizer.init_state == "loaded"


def test_load_no_tokenizer_dir(test_config):
    factory.create_tokenizer(test_config)

    test_config.project_dir = test_config.project_dir / 'foo'

    with pytest.raises(UsageError):
        factory.get_tokenizer_for_db(test_config)


def test_load_missing_propoerty(temp_db_cursor, test_config):
    factory.create_tokenizer(test_config)

    temp_db_cursor.execute("TRUNCATE TABLE nominatim_properties")

    with pytest.raises(UsageError):
        factory.get_tokenizer_for_db(test_config)
