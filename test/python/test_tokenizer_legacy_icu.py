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


def test_init_word_table(tokenizer_factory, test_config, place_row, word_table):
    place_row(names={'name' : 'Test Area', 'ref' : '52'})
    place_row(names={'name' : 'No Area'})
    place_row(names={'name' : 'Holzstrasse'})

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert word_table.get_partial_words() == {('test', 1), ('52', 1),
                                              ('no', 1), ('area', 2),
                                              ('holzstrasse', 1), ('holzstr', 1),
                                              ('holz', 1), ('strasse', 1),
                                              ('str', 1)}


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


def test_normalize_postcode(analyzer):
    with analyzer() as anl:
        anl.normalize_postcode('123') == '123'
        anl.normalize_postcode('ab-34 ') == 'AB-34'
        anl.normalize_postcode('38 Б') == '38 Б'


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


def test_add_country_names_new(analyzer, word_table):
    with analyzer() as anl:
        anl.add_country_names('es', {'name': 'Espagña', 'name:en': 'Spain'})

    assert word_table.get_country() == {('es', ' ESPAGÑA'), ('es', ' SPAIN')}


def test_add_country_names_extend(analyzer, word_table):
    word_table.add_country('ch', ' SCHWEIZ')

    with analyzer() as anl:
        anl.add_country_names('ch', {'name': 'Schweiz', 'name:fr': 'Suisse'})

    assert word_table.get_country() == {('ch', ' SCHWEIZ'), ('ch', ' SUISSE')}


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
        info = self.analyzer.process_place({'name': {'name': 'Soft bAr', 'ref': '34'}})

        self.expect_name_terms(info, '#Soft bAr', '#34','Soft', 'bAr', '34')


    @pytest.mark.parametrize('sep', [',' , ';'])
    def test_names_with_separator(self, sep):
        info = self.analyzer.process_place({'name': {'name': sep.join(('New York', 'Big Apple'))}})

        self.expect_name_terms(info, '#New York', '#Big Apple',
                                     'new', 'york', 'big', 'apple')


    def test_full_names_with_bracket(self):
        info = self.analyzer.process_place({'name': {'name': 'Houseboat (left)'}})

        self.expect_name_terms(info, '#Houseboat (left)', '#Houseboat',
                                     'houseboat', 'left')


    def test_country_name(self, word_table):
        info = self.analyzer.process_place({'name': {'name': 'Norge'},
                                           'country_feature': 'no'})

        self.expect_name_terms(info, '#norge', 'norge')
        assert word_table.get_country() == {('no', ' NORGE')}


class TestPlaceAddress:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer, getorcreate_full_word):
        with analyzer(trans=(":: upper()", "'🜵' > ' '")) as anl:
            self.analyzer = anl
            yield anl


    def process_address(self, **kwargs):
        return self.analyzer.process_place({'address': kwargs})


    def name_token_set(self, *expected_terms):
        tokens = self.analyzer.get_word_token_info(expected_terms)
        for token in tokens:
            assert token[2] is not None, "No token for {0}".format(token)

        return set((t[2] for t in tokens))


    @pytest.mark.parametrize('pcode', ['12345', 'AB 123', '34-345'])
    def test_process_place_postcode(self, word_table, pcode):
        self.process_address(postcode=pcode)

        assert word_table.get_postcodes() == {pcode, }


    @pytest.mark.parametrize('pcode', ['12:23', 'ab;cd;f', '123;836'])
    def test_process_place_bad_postcode(self, word_table, pcode):
        self.process_address(postcode=pcode)

        assert not word_table.get_postcodes()


    @pytest.mark.parametrize('hnr', ['123a', '1', '101'])
    def test_process_place_housenumbers_simple(self, hnr, getorcreate_hnr_id):
        info = self.process_address(housenumber=hnr)

        assert info['hnr'] == hnr.upper()
        assert info['hnr_tokens'] == "{-1}"


    def test_process_place_housenumbers_lists(self, getorcreate_hnr_id):
        info = self.process_address(conscriptionnumber='1; 2;3')

        assert set(info['hnr'].split(';')) == set(('1', '2', '3'))
        assert info['hnr_tokens'] == "{-1,-2,-3}"


    def test_process_place_housenumbers_duplicates(self, getorcreate_hnr_id):
        info = self.process_address(housenumber='134',
                                    conscriptionnumber='134',
                                    streetnumber='99a')

        assert set(info['hnr'].split(';')) == set(('134', '99A'))
        assert info['hnr_tokens'] == "{-1,-2}"


    def test_process_place_housenumbers_cached(self, getorcreate_hnr_id):
        info = self.process_address(housenumber="45")
        assert info['hnr_tokens'] == "{-1}"

        info = self.process_address(housenumber="46")
        assert info['hnr_tokens'] == "{-2}"

        info = self.process_address(housenumber="41;45")
        assert eval(info['hnr_tokens']) == {-1, -3}

        info = self.process_address(housenumber="41")
        assert eval(info['hnr_tokens']) == {-3}


    def test_process_place_street(self):
        info = self.process_address(street='Grand Road')

        assert eval(info['street']) == self.name_token_set('#GRAND ROAD')


    def test_process_place_street_empty(self):
        info = self.process_address(street='🜵')

        assert 'street' not in info


    def test_process_place_place(self):
        info = self.process_address(place='Honu Lulu')

        assert eval(info['place_search']) == self.name_token_set('#HONU LULU',
                                                                 'HONU', 'LULU')
        assert eval(info['place_match']) == self.name_token_set('#HONU LULU')


    def test_process_place_place_empty(self):
        info = self.process_address(place='🜵')

        assert 'place_search' not in info
        assert 'place_match' not in info


    def test_process_place_address_terms(self):
        info = self.process_address(country='de', city='Zwickau', state='Sachsen',
                                    suburb='Zwickau', street='Hauptstr',
                                    full='right behind the church')

        city_full = self.name_token_set('#ZWICKAU')
        city_all = self.name_token_set('#ZWICKAU', 'ZWICKAU')
        state_full = self.name_token_set('#SACHSEN')
        state_all = self.name_token_set('#SACHSEN', 'SACHSEN')

        result = {k: [eval(v[0]), eval(v[1])] for k,v in info['addr'].items()}

        assert result == {'city': [city_all, city_full],
                          'suburb': [city_all, city_full],
                          'state': [state_all, state_full]}


    def test_process_place_address_terms_empty(self):
        info = self.process_address(country='de', city=' ', street='Hauptstr',
                                    full='right behind the church')

        assert 'addr' not in info

