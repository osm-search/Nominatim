"""
Tests for Legacy ICU tokenizer.
"""
import shutil

import pytest

from nominatim.tokenizer import legacy_icu_tokenizer
from nominatim.db import properties


@pytest.fixture
def test_config(def_config, tmp_path):
    def_config.project_dir = tmp_path / 'project'
    def_config.project_dir.mkdir()

    sqldir = tmp_path / 'sql'
    sqldir.mkdir()
    (sqldir / 'tokenizer').mkdir()
    (sqldir / 'tokenizer' / 'legacy_icu_tokenizer.sql').write_text("SELECT 'a'")
    shutil.copy(str(def_config.lib_dir.sql / 'tokenizer' / 'legacy_tokenizer_tables.sql'),
                str(sqldir / 'tokenizer' / 'legacy_tokenizer_tables.sql'))

    def_config.lib_dir.sql = sqldir

    return def_config


@pytest.fixture
def tokenizer_factory(dsn, tmp_path, property_table,
                      sql_preprocessor, place_table, word_table):
    (tmp_path / 'tokenizer').mkdir()

    def _maker():
        return legacy_icu_tokenizer.create(dsn, tmp_path / 'tokenizer')

    return _maker


@pytest.fixture
def db_prop(temp_db_conn):
    def _get_db_property(name):
        return properties.get_property(temp_db_conn,
                                       getattr(legacy_icu_tokenizer, name))

    return _get_db_property

@pytest.fixture
def tokenizer_setup(tokenizer_factory, test_config, monkeypatch, sql_preprocessor):
    tok = tokenizer_factory()
    tok.init_new_db(test_config)


@pytest.fixture
def analyzer(tokenizer_factory, test_config, monkeypatch, sql_preprocessor,
             word_table, temp_db_with_extensions, tmp_path):
    sql = tmp_path / 'sql' / 'tokenizer' / 'legacy_icu_tokenizer.sql'
    sql.write_text("SELECT 'a';")

    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    def _mk_analyser(trans=':: upper();', abbr=(('STREET', 'ST'), )):
        tok.transliteration = trans
        tok.abbreviations = abbr

        return tok.name_analyzer()

    return _mk_analyser


@pytest.fixture
def getorcreate_term_id(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_term_id(lookup_term TEXT)
                              RETURNS INTEGER AS $$ SELECT nextval('seq_word')::INTEGER; $$ LANGUAGE SQL""")


@pytest.fixture
def getorcreate_hnr_id(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_hnr_id(lookup_term TEXT)
                              RETURNS INTEGER AS $$ SELECT -nextval('seq_word')::INTEGER; $$ LANGUAGE SQL""")


def test_init_new(tokenizer_factory, test_config, monkeypatch, db_prop,
                  sql_preprocessor, place_table, word_table):
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert db_prop('DBCFG_NORMALIZATION') == ':: lower();'
    assert db_prop('DBCFG_TRANSLITERATION') is not None
    assert db_prop('DBCFG_ABBREVIATIONS') is not None


def test_init_from_project(tokenizer_setup, tokenizer_factory):
    tok = tokenizer_factory()

    tok.init_from_project()

    assert tok.normalization is not None
    assert tok.transliteration is not None
    assert tok.abbreviations is not None


def test_update_sql_functions(temp_db_conn, db_prop, temp_db_cursor,
                              tokenizer_factory, test_config, table_factory,
                              monkeypatch,
                              sql_preprocessor, place_table, word_table):
    monkeypatch.setenv('NOMINATIM_MAX_WORD_FREQUENCY', '1133')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    assert db_prop('DBCFG_MAXWORDFREQ') == '1133'

    table_factory('test', 'txt TEXT')

    func_file = test_config.lib_dir.sql / 'tokenizer' / 'legacy_icu_tokenizer.sql'
    func_file.write_text("""INSERT INTO test VALUES ('{{max_word_freq}}')""")

    tok.update_sql_functions(test_config)

    test_content = temp_db_cursor.row_set('SELECT * FROM test')
    assert test_content == set((('1133', ), ))


def test_make_standard_word(analyzer):
    with analyzer(abbr=(('STREET', 'ST'), ('tiny', 't'))) as a:
        assert a.make_standard_word('tiny street') == 'TINY ST'

    with analyzer(abbr=(('STRASSE', 'STR'), ('STR', 'ST'))) as a:
        assert a.make_standard_word('Hauptstrasse') == 'HAUPTST'


def test_make_standard_hnr(analyzer):
    with analyzer(abbr=(('IV', '4'),)) as a:
        assert a._make_standard_hnr('345') == '345'
        assert a._make_standard_hnr('iv') == 'IV'


def test_add_postcodes_from_db(analyzer, word_table, table_factory, temp_db_cursor):
    table_factory('location_postcode', 'postcode TEXT',
                  content=(('1234',), ('12 34',), ('AB23',), ('1234',)))

    with analyzer() as a:
        a.add_postcodes_from_db()

    assert temp_db_cursor.row_set("""SELECT word, word_token from word
                                     """) \
               == set((('1234', ' 1234'), ('12 34', ' 12 34'), ('AB23', ' AB23')))


def test_update_special_phrase_empty_table(analyzer, word_table, temp_db_cursor):
    with analyzer() as a:
        a.update_special_phrases([
            ("König bei", "amenity", "royal", "near"),
            ("Könige", "amenity", "royal", "-"),
            ("street", "highway", "primary", "in")
        ], True)

    assert temp_db_cursor.row_set("""SELECT word_token, word, class, type, operator
                                     FROM word WHERE class != 'place'""") \
               == set(((' KÖNIG BEI', 'könig bei', 'amenity', 'royal', 'near'),
                       (' KÖNIGE', 'könige', 'amenity', 'royal', None),
                       (' ST', 'street', 'highway', 'primary', 'in')))


def test_update_special_phrase_delete_all(analyzer, word_table, temp_db_cursor):
    temp_db_cursor.execute("""INSERT INTO word (word_token, word, class, type, operator)
                              VALUES (' FOO', 'foo', 'amenity', 'prison', 'in'),
                                     (' BAR', 'bar', 'highway', 'road', null)""")

    assert 2 == temp_db_cursor.scalar("SELECT count(*) FROM word WHERE class != 'place'""")

    with analyzer() as a:
        a.update_special_phrases([], True)

    assert 0 == temp_db_cursor.scalar("SELECT count(*) FROM word WHERE class != 'place'""")


def test_update_special_phrases_no_replace(analyzer, word_table, temp_db_cursor,):
    temp_db_cursor.execute("""INSERT INTO word (word_token, word, class, type, operator)
                              VALUES (' FOO', 'foo', 'amenity', 'prison', 'in'),
                                     (' BAR', 'bar', 'highway', 'road', null)""")

    assert 2 == temp_db_cursor.scalar("SELECT count(*) FROM word WHERE class != 'place'""")

    with analyzer() as a:
        a.update_special_phrases([], False)

    assert 2 == temp_db_cursor.scalar("SELECT count(*) FROM word WHERE class != 'place'""")


def test_update_special_phrase_modify(analyzer, word_table, temp_db_cursor):
    temp_db_cursor.execute("""INSERT INTO word (word_token, word, class, type, operator)
                              VALUES (' FOO', 'foo', 'amenity', 'prison', 'in'),
                                     (' BAR', 'bar', 'highway', 'road', null)""")

    assert 2 == temp_db_cursor.scalar("SELECT count(*) FROM word WHERE class != 'place'""")

    with analyzer() as a:
        a.update_special_phrases([
          ('prison', 'amenity', 'prison', 'in'),
          ('bar', 'highway', 'road', '-'),
          ('garden', 'leisure', 'garden', 'near')
        ], True)

    assert temp_db_cursor.row_set("""SELECT word_token, word, class, type, operator
                                     FROM word WHERE class != 'place'""") \
               == set(((' PRISON', 'prison', 'amenity', 'prison', 'in'),
                       (' BAR', 'bar', 'highway', 'road', None),
                       (' GARDEN', 'garden', 'leisure', 'garden', 'near')))


def test_process_place_names(analyzer, getorcreate_term_id):

    with analyzer() as a:
        info = a.process_place({'name' : {'name' : 'Soft bAr', 'ref': '34'}})

    assert info['names'] == '{1,2,3,4,5,6}'


@pytest.mark.parametrize('pc', ['12345', 'AB 123', '34-345'])
def test_process_place_postcode(analyzer, temp_db_cursor, pc):
    with analyzer() as a:
        info = a.process_place({'address': {'postcode' : pc}})

    assert temp_db_cursor.row_set("""SELECT word FROM word
                                     WHERE class = 'place' and type = 'postcode'""") \
               == set(((pc, ),))


@pytest.mark.parametrize('pc', ['12:23', 'ab;cd;f', '123;836'])
def test_process_place_bad_postcode(analyzer, temp_db_cursor, pc):
    with analyzer() as a:
        info = a.process_place({'address': {'postcode' : pc}})

    assert 0 == temp_db_cursor.scalar("""SELECT count(*) FROM word
                                         WHERE class = 'place' and type = 'postcode'""")


@pytest.mark.parametrize('hnr', ['123a', '1', '101'])
def test_process_place_housenumbers_simple(analyzer, hnr, getorcreate_hnr_id):
    with analyzer() as a:
        info = a.process_place({'address': {'housenumber' : hnr}})

    assert info['hnr'] == hnr.upper()
    assert info['hnr_tokens'] == "{-1}"


def test_process_place_housenumbers_lists(analyzer, getorcreate_hnr_id):
    with analyzer() as a:
        info = a.process_place({'address': {'conscriptionnumber' : '1; 2;3'}})

    assert set(info['hnr'].split(';')) == set(('1', '2', '3'))
    assert info['hnr_tokens'] == "{-1,-2,-3}"


def test_process_place_housenumbers_duplicates(analyzer, getorcreate_hnr_id):
    with analyzer() as a:
        info = a.process_place({'address': {'housenumber' : '134',
                                               'conscriptionnumber' : '134',
                                               'streetnumber' : '99a'}})

    assert set(info['hnr'].split(';')) == set(('134', '99A'))
    assert info['hnr_tokens'] == "{-1,-2}"
