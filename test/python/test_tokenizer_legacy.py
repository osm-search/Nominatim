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
def tokenizer_factory(dsn, tmp_path, property_table):
    (tmp_path / 'tokenizer').mkdir()

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


@pytest.fixture
def make_standard_name(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION make_standard_name(name TEXT)
                              RETURNS TEXT AS $$ SELECT ' ' || name; $$ LANGUAGE SQL""")


@pytest.fixture
def create_postcode_id(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION create_postcode_id(postcode TEXT)
                              RETURNS BOOLEAN AS $$
                              INSERT INTO word (word_token, word, class, type)
                                VALUES (' ' || postcode, postcode, 'place', 'postcode')
                              RETURNING True;
                              $$ LANGUAGE SQL""")


@pytest.fixture
def create_housenumbers(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION create_housenumbers(
                                  housenumbers TEXT[],
                                  OUT tokens TEXT, OUT normtext TEXT)
                              AS $$
                              SELECT housenumbers::TEXT, array_to_string(housenumbers, ';')
                              $$ LANGUAGE SQL""")


@pytest.fixture
def make_keywords(temp_db_cursor, temp_db_with_extensions):
    temp_db_cursor.execute(
        """CREATE OR REPLACE FUNCTION make_keywords(names HSTORE)
           RETURNS INTEGER[] AS $$ SELECT ARRAY[1, 2, 3] $$ LANGUAGE SQL""")

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


def test_update_postcodes_from_db_empty(analyzer, table_factory, word_table,
                                        create_postcode_id):
    table_factory('location_postcode', 'postcode TEXT',
                  content=(('1234',), ('12 34',), ('AB23',), ('1234',)))

    analyzer.update_postcodes_from_db()

    assert word_table.count() == 3
    assert word_table.get_postcodes() == {'1234', '12 34', 'AB23'}


def test_update_postcodes_from_db_add_and_remove(analyzer, table_factory, word_table,
                                                 create_postcode_id):
    table_factory('location_postcode', 'postcode TEXT',
                  content=(('1234',), ('45BC', ), ('XX45', )))
    word_table.add_postcode(' 1234', '1234')
    word_table.add_postcode(' 5678', '5678')

    analyzer.update_postcodes_from_db()

    assert word_table.count() == 3
    assert word_table.get_postcodes() == {'1234', '45BC', 'XX45'}


def test_update_special_phrase_empty_table(analyzer, word_table, make_standard_name):
    analyzer.update_special_phrases([
        ("König bei", "amenity", "royal", "near"),
        ("Könige", "amenity", "royal", "-"),
        ("strasse", "highway", "primary", "in")
    ], True)

    assert word_table.get_special() \
               == set(((' könig bei', 'könig bei', 'amenity', 'royal', 'near'),
                       (' könige', 'könige', 'amenity', 'royal', None),
                       (' strasse', 'strasse', 'highway', 'primary', 'in')))


def test_update_special_phrase_delete_all(analyzer, word_table, temp_db_cursor,
                                          make_standard_name):
    word_table.add_special(' foo', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' bar', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    analyzer.update_special_phrases([], True)

    assert word_table.count_special() == 0


def test_update_special_phrases_no_replace(analyzer, word_table, temp_db_cursor,
                                          make_standard_name):
    temp_db_cursor.execute("""INSERT INTO word (word_token, word, class, type, operator)
                              VALUES (' foo', 'foo', 'amenity', 'prison', 'in'),
                                     (' bar', 'bar', 'highway', 'road', null)""")

    assert word_table.count_special() == 2

    analyzer.update_special_phrases([], False)

    assert word_table.count_special() == 2


def test_update_special_phrase_modify(analyzer, word_table, make_standard_name):
    word_table.add_special(' foo', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' bar', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    analyzer.update_special_phrases([
      ('prison', 'amenity', 'prison', 'in'),
      ('bar', 'highway', 'road', '-'),
      ('garden', 'leisure', 'garden', 'near')
    ], True)

    assert word_table.get_special() \
               == set(((' prison', 'prison', 'amenity', 'prison', 'in'),
                       (' bar', 'bar', 'highway', 'road', None),
                       (' garden', 'garden', 'leisure', 'garden', 'near')))


def test_process_place_names(analyzer, make_keywords):

    info = analyzer.process_place({'name' : {'name' : 'Soft bAr', 'ref': '34'}})

    assert info['names'] == '{1,2,3}'


@pytest.mark.parametrize('pc', ['12345', 'AB 123', '34-345'])
def test_process_place_postcode(analyzer, create_postcode_id, word_table, pc):
    info = analyzer.process_place({'address': {'postcode' : pc}})

    assert word_table.get_postcodes() == {pc, }


@pytest.mark.parametrize('pc', ['12:23', 'ab;cd;f', '123;836'])
def test_process_place_bad_postcode(analyzer, create_postcode_id, word_table, pc):
    info = analyzer.process_place({'address': {'postcode' : pc}})

    assert not word_table.get_postcodes()


@pytest.mark.parametrize('hnr', ['123a', '1', '101'])
def test_process_place_housenumbers_simple(analyzer, create_housenumbers, hnr):
    info = analyzer.process_place({'address': {'housenumber' : hnr}})

    assert info['hnr'] == hnr
    assert info['hnr_tokens'].startswith("{")


def test_process_place_housenumbers_lists(analyzer, create_housenumbers):
    info = analyzer.process_place({'address': {'conscriptionnumber' : '1; 2;3'}})

    assert set(info['hnr'].split(';')) == set(('1', '2', '3'))


def test_process_place_housenumbers_duplicates(analyzer, create_housenumbers):
    info = analyzer.process_place({'address': {'housenumber' : '134',
                                               'conscriptionnumber' : '134',
                                               'streetnumber' : '99a'}})

    assert set(info['hnr'].split(';')) == set(('134', '99a'))
