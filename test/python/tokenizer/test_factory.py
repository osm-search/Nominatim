"""
Tests for creating new tokenizers.
"""
import pytest

from nominatim.db import properties
from nominatim.tokenizer import factory
from nominatim.errors import UsageError
from dummy_tokenizer import DummyTokenizer


def test_setup_bad_tokenizer_name(project_env, monkeypatch):
    monkeypatch.setenv('NOMINATIM_TOKENIZER', 'dummy')

    with pytest.raises(UsageError):
        factory.create_tokenizer(project_env)


class TestFactory:
    @pytest.fixture(autouse=True)
    def init_env(self, project_env, property_table, tokenizer_mock):
        self.config = project_env


    def test_setup_dummy_tokenizer(self, temp_db_conn):
        tokenizer = factory.create_tokenizer(self.config)

        assert isinstance(tokenizer, DummyTokenizer)
        assert tokenizer.init_state == "new"
        assert (self.config.project_dir / 'tokenizer').is_dir()

        assert properties.get_property(temp_db_conn, 'tokenizer') == 'dummy'


    def test_setup_tokenizer_dir_exists(self):
        (self.config.project_dir / 'tokenizer').mkdir()

        tokenizer = factory.create_tokenizer(self.config)

        assert isinstance(tokenizer, DummyTokenizer)
        assert tokenizer.init_state == "new"


    def test_setup_tokenizer_dir_failure(self):
        (self.config.project_dir / 'tokenizer').write_text("foo")

        with pytest.raises(UsageError):
            factory.create_tokenizer(self.config)


    def test_load_tokenizer(self):
        factory.create_tokenizer(self.config)

        tokenizer = factory.get_tokenizer_for_db(self.config)

        assert isinstance(tokenizer, DummyTokenizer)
        assert tokenizer.init_state == "loaded"


    def test_load_no_tokenizer_dir(self):
        factory.create_tokenizer(self.config)

        self.config.project_dir = self.config.project_dir / 'foo'

        with pytest.raises(UsageError):
            factory.get_tokenizer_for_db(self.config)


    def test_load_missing_property(self, temp_db_cursor):
        factory.create_tokenizer(self.config)

        temp_db_cursor.execute("TRUNCATE TABLE nominatim_properties")

        with pytest.raises(UsageError):
            factory.get_tokenizer_for_db(self.config)
