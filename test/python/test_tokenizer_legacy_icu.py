"""
Tests for Legacy ICU tokenizer.
"""
import shutil
import yaml

import pytest

from nominatim.tokenizer import legacy_icu_tokenizer
from nominatim.tokenizer.icu_name_processor import ICUNameProcessorRules
from nominatim.tokenizer.icu_rule_loader import ICURuleLoader
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
        return properties.get_property(temp_db_conn, name)

    return _get_db_property


@pytest.fixture
def analyzer(tokenizer_factory, test_config, monkeypatch,
             temp_db_with_extensions, tmp_path):
    sql = tmp_path / 'sql' / 'tokenizer' / 'legacy_icu_tokenizer.sql'
    sql.write_text("SELECT 'a';")

    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    def _mk_analyser(norm=("[[:Punctuation:][:Space:]]+ > ' '",), trans=(':: upper()',),
                     suffixes=('gasse', ), abbr=('street => st', )):
        cfgfile = tmp_path / 'analyser_test_config.yaml'
        with cfgfile.open('w') as stream:
            cfgstr = {'normalization' : list(norm),
                       'transliteration' : list(trans),
                       'compound_suffixes' : list(suffixes),
                       'abbreviations' : list(abbr)}
            yaml.dump(cfgstr, stream)
        tok.naming_rules = ICUNameProcessorRules(loader=ICURuleLoader(cfgfile))

        return tok.name_analyzer()

    return _mk_analyser


@pytest.fixture
def getorcreate_full_word(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_full_word(
                                                 norm_term TEXT, lookup_terms TEXT[],
                                                 OUT full_token INT,
                                                 OUT partial_tokens INT[])
  AS $$
DECLARE
  partial_terms TEXT[] = '{}'::TEXT[];
  term TEXT;
  term_id INTEGER;
  term_count INTEGER;
BEGIN
  SELECT min(word_id) INTO full_token
    FROM word WHERE word = norm_term and class is null and country_code is null;

  IF full_token IS NULL THEN
    full_token := nextval('seq_word');
    INSERT INTO word (word_id, word_token, word, search_name_count)
      SELECT full_token, ' ' || lookup_term, norm_term, 0 FROM unnest(lookup_terms) as lookup_term;
  END IF;

  FOR term IN SELECT unnest(string_to_array(unnest(lookup_terms), ' ')) LOOP
    term := trim(term);
    IF NOT (ARRAY[term] <@ partial_terms) THEN
      partial_terms := partial_terms || term;
    END IF;
  END LOOP;

  partial_tokens := '{}'::INT[];
  FOR term IN SELECT unnest(partial_terms) LOOP
    SELECT min(word_id), max(search_name_count) INTO term_id, term_count
      FROM word WHERE word_token = term and class is null and country_code is null;

    IF term_id IS NULL THEN
      term_id := nextval('seq_word');
      term_count := 0;
      INSERT INTO word (word_id, word_token, search_name_count)
        VALUES (term_id, term, 0);
    END IF;

    IF NOT (ARRAY[term_id] <@ partial_tokens) THEN
        partial_tokens := partial_tokens || term_id;
    END IF;
  END LOOP;
END;
$$
LANGUAGE plpgsql;
                              """)


@pytest.fixture
def getorcreate_hnr_id(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_hnr_id(lookup_term TEXT)
                              RETURNS INTEGER AS $$
                                SELECT -nextval('seq_word')::INTEGER; $$ LANGUAGE SQL""")


def test_init_new(tokenizer_factory, test_config, monkeypatch, db_prop):
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert db_prop(legacy_icu_tokenizer.DBCFG_TERM_NORMALIZATION) == ':: lower();'
    assert db_prop(legacy_icu_tokenizer.DBCFG_MAXWORDFREQ) is not None


def test_init_from_project(monkeypatch, test_config, tokenizer_factory):
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')
    monkeypatch.setenv('NOMINATIM_MAX_WORD_FREQUENCY', '90300')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    tok = tokenizer_factory()
    tok.init_from_project()

    assert tok.naming_rules is not None
    assert tok.term_normalization == ':: lower();'
    assert tok.max_word_frequency == '90300'


def test_update_sql_functions(db_prop, temp_db_cursor,
                              tokenizer_factory, test_config, table_factory,
                              monkeypatch):
    monkeypatch.setenv('NOMINATIM_MAX_WORD_FREQUENCY', '1133')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    assert db_prop(legacy_icu_tokenizer.DBCFG_MAXWORDFREQ) == '1133'

    table_factory('test', 'txt TEXT')

    func_file = test_config.lib_dir.sql / 'tokenizer' / 'legacy_icu_tokenizer.sql'
    func_file.write_text("""INSERT INTO test VALUES ('{{max_word_freq}}')""")

    tok.update_sql_functions(test_config)

    test_content = temp_db_cursor.row_set('SELECT * FROM test')
    assert test_content == set((('1133', ), ))


def test_make_standard_hnr(analyzer):
    with analyzer(abbr=('IV => 4',)) as anl:
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
            ("König  bei", "amenity", "royal", "near"),
            ("Könige ", "amenity", "royal", "-"),
            ("street", "highway", "primary", "in")
        ], True)

    assert word_table.get_special() \
               == {(' KÖNIG BEI', 'König bei', 'amenity', 'royal', 'near'),
                   (' KÖNIGE', 'Könige', 'amenity', 'royal', None),
                   (' STREET', 'street', 'highway', 'primary', 'in')}


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


class TestPlaceNames:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer, getorcreate_full_word):
        with analyzer() as anl:
            self.analyzer = anl
            yield anl


    def expect_name_terms(self, info, *expected_terms):
        tokens = self.analyzer.get_word_token_info(expected_terms)
        for token in tokens:
            assert token[2] is not None, "No token for {0}".format(token)

        assert eval(info['names']) == set((t[2] for t in tokens))


    def test_simple_names(self):
        info = self.analyzer.process_place({'name' : {'name' : 'Soft bAr', 'ref': '34'}})

        self.expect_name_terms(info, '#Soft bAr', '#34','Soft', 'bAr', '34')


    @pytest.mark.parametrize('sep', [',' , ';'])
    def test_names_with_separator(self, sep):
        info = self.analyzer.process_place({'name' : {'name' : sep.join(('New York', 'Big Apple'))}})

        self.expect_name_terms(info, '#New York', '#Big Apple',
                                     'new', 'york', 'big', 'apple')


    def test_full_names_with_bracket(self):
        info = self.analyzer.process_place({'name' : {'name' : 'Houseboat (left)'}})

        self.expect_name_terms(info, '#Houseboat (left)', '#Houseboat',
                                     'houseboat', 'left')


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
