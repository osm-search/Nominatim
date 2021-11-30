"""
Tests for creating PL/pgSQL functions for Nominatim.
"""
import pytest

from nominatim.tools.refresh import create_functions

class TestCreateFunctions:
    @pytest.fixture(autouse=True)
    def init_env(self, sql_preprocessor, temp_db_conn, def_config, tmp_path):
        self.conn = temp_db_conn
        self.config = def_config
        def_config.lib_dir.sql = tmp_path


    def write_functions(self, content):
        sqlfile = self.config.lib_dir.sql / 'functions.sql'
        sqlfile.write_text(content)


    def test_create_functions(self, temp_db_cursor):
        self.write_functions("""CREATE OR REPLACE FUNCTION test() RETURNS INTEGER
                              AS $$
                              BEGIN
                                RETURN 43;
                              END;
                              $$ LANGUAGE plpgsql IMMUTABLE;
                           """)

        create_functions(self.conn, self.config)

        assert temp_db_cursor.scalar('SELECT test()') == 43


    @pytest.mark.parametrize("dbg,ret", ((True, 43), (False, 22)))
    def test_create_functions_with_template(self, temp_db_cursor, dbg, ret):
        self.write_functions("""CREATE OR REPLACE FUNCTION test() RETURNS INTEGER
                              AS $$
                              BEGIN
                                {% if debug %}
                                RETURN 43;
                                {% else %}
                                RETURN 22;
                                {% endif %}
                              END;
                              $$ LANGUAGE plpgsql IMMUTABLE;
                           """)

        create_functions(self.conn, self.config, enable_debug=dbg)

        assert temp_db_cursor.scalar('SELECT test()') == ret
