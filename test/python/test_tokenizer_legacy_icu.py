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
def tokenizer_setup(tokenizer_factory, test_config):
    tok = tokenizer_factory()
    tok.init_new_db(test_config)


@pytest.fixture
def analyzer(tokenizer_factory, test_config, monkeypatch,
             temp_db_with_extensions, tmp_path):
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
                              RETURNS INTEGER AS $$
                                SELECT nextval('seq_word')::INTEGER; $$ LANGUAGE SQL""")


@pytest.fixture
def getorcreate_hnr_id(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_hnr_id(lookup_term TEXT)
                              RETURNS INTEGER AS $$
                                SELECT -nextval('seq_word')::INTEGER; $$ LANGUAGE SQL""")


def test_init_new(tokenizer_factory, test_config, monkeypatch, db_prop):
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


def test_update_sql_functions(db_prop, temp_db_cursor,
                              tokenizer_factory, test_config, table_factory,
                              monkeypatch):
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
    with analyzer(abbr=(('STREET', 'ST'), ('tiny', 't'))) as anl:
        assert anl.make_standard_word('tiny street') == 'TINY ST'

    with analyzer(abbr=(('STRASSE', 'STR'), ('STR', 'ST'))) as anl:
        assert anl.make_standard_word('Hauptstrasse') == 'HAUPTST'


def test_make_standard_hnr(analyzer):
    with analyzer(abbr=(('IV', '4'),)) as anl:
        assert anl._make_standard_hnr('345') == '345'
        assert anl._make_standard_hnr('iv') == 'IV'


def test_update_postcodes_from_db_empty(analyzer, table_factory, word_table):
    table_factory('location_postcode', 'postcode TEXT',
                  content=(('1234',), ('12 34',), ('AB23',), ('1234',)))

    with analyzer() as anl:
        anl.update_postcodes_from_db()

    assert word_table.count() == 3
    assert word_table.get_postcodes() == {'1234', '12 34', 'AB23'}


def test_update_postcodes_from_db_add_and_remove(analyzer, table_factory, word_table):
    table_factory('location_postcode', 'postcode TEXT',
                  content=(('1234',), ('45BC', ), ('XX45', )))
    word_table.add_postcode(' 1234', '1234')
    word_table.add_postcode(' 5678', '5678')

    with analyzer() as anl:
        anl.update_postcodes_from_db()

    assert word_table.count() == 3
    assert word_table.get_postcodes() == {'1234', '45BC', 'XX45'}


def test_update_special_phrase_empty_table(analyzer, word_table):
    with analyzer() as anl:
        anl.update_special_phrases([
            ("König bei", "amenity", "royal", "near"),
            ("Könige", "amenity", "royal", "-"),
            ("street", "highway", "primary", "in")
        ], True)

    assert word_table.get_special() \
               == {(' KÖNIG BEI', 'könig bei', 'amenity', 'royal', 'near'),
                   (' KÖNIGE', 'könige', 'amenity', 'royal', None),
                   (' ST', 'street', 'highway', 'primary', 'in')}


def test_update_special_phrase_delete_all(analyzer, word_table):
    word_table.add_special(' FOO', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' BAR', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    with analyzer() as anl:
        anl.update_special_phrases([], True)

    assert word_table.count_special() == 0


def test_update_special_phrases_no_replace(analyzer, word_table):
    word_table.add_special(' FOO', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' BAR', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    with analyzer() as anl:
        anl.update_special_phrases([], False)

    assert word_table.count_special() == 2


def test_update_special_phrase_modify(analyzer, word_table):
    word_table.add_special(' FOO', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' BAR', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    with analyzer() as anl:
        anl.update_special_phrases([
            ('prison', 'amenity', 'prison', 'in'),
            ('bar', 'highway', 'road', '-'),
            ('garden', 'leisure', 'garden', 'near')
        ], True)

    assert word_table.get_special() \
               == {(' PRISON', 'prison', 'amenity', 'prison', 'in'),
                   (' BAR', 'bar', 'highway', 'road', None),
                   (' GARDEN', 'garden', 'leisure', 'garden', 'near')}


def test_process_place_names(analyzer, getorcreate_term_id):
    with analyzer() as anl:
        info = anl.process_place({'name' : {'name' : 'Soft bAr', 'ref': '34'}})

    assert info['names'] == '{1,2,3,4,5}'


@pytest.mark.parametrize('sep', [',' , ';'])
def test_full_names_with_separator(analyzer, getorcreate_term_id, sep):
    with analyzer() as anl:
        names = anl._compute_full_names({'name' : sep.join(('New York', 'Big Apple'))})

    assert names == set(('NEW YORK', 'BIG APPLE'))


def test_full_names_with_bracket(analyzer, getorcreate_term_id):
    with analyzer() as anl:
        names = anl._compute_full_names({'name' : 'Houseboat (left)'})

    assert names == set(('HOUSEBOAT (LEFT)', 'HOUSEBOAT'))


@pytest.mark.parametrize('pcode', ['12345', 'AB 123', '34-345'])
def test_process_place_postcode(analyzer, word_table, pcode):
    with analyzer() as anl:
        anl.process_place({'address': {'postcode' : pcode}})

    assert word_table.get_postcodes() == {pcode, }


@pytest.mark.parametrize('pcode', ['12:23', 'ab;cd;f', '123;836'])
def test_process_place_bad_postcode(analyzer, word_table, pcode):
    with analyzer() as anl:
        anl.process_place({'address': {'postcode' : pcode}})

    assert not word_table.get_postcodes()


@pytest.mark.parametrize('hnr', ['123a', '1', '101'])
def test_process_place_housenumbers_simple(analyzer, hnr, getorcreate_hnr_id):
    with analyzer() as anl:
        info = anl.process_place({'address': {'housenumber' : hnr}})

    assert info['hnr'] == hnr.upper()
    assert info['hnr_tokens'] == "{-1}"


def test_process_place_housenumbers_lists(analyzer, getorcreate_hnr_id):
    with analyzer() as anl:
        info = anl.process_place({'address': {'conscriptionnumber' : '1; 2;3'}})

    assert set(info['hnr'].split(';')) == set(('1', '2', '3'))
    assert info['hnr_tokens'] == "{-1,-2,-3}"


def test_process_place_housenumbers_duplicates(analyzer, getorcreate_hnr_id):
    with analyzer() as anl:
        info = anl.process_place({'address': {'housenumber' : '134',
                                              'conscriptionnumber' : '134',
                                              'streetnumber' : '99a'}})

    assert set(info['hnr'].split(';')) == set(('134', '99A'))
    assert info['hnr_tokens'] == "{-1,-2}"
