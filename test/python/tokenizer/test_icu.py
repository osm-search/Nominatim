# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for ICU tokenizer.
"""
import shutil
import yaml
import itertools

import pytest

from nominatim.tokenizer import icu_tokenizer
import nominatim.tokenizer.icu_rule_loader
from nominatim.db import properties
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.data.place_info import PlaceInfo

from mock_icu_word_table import MockIcuWordTable

@pytest.fixture
def word_table(temp_db_conn):
    return MockIcuWordTable(temp_db_conn)


@pytest.fixture
def test_config(project_env, tmp_path):
    sqldir = tmp_path / 'sql'
    sqldir.mkdir()
    (sqldir / 'tokenizer').mkdir()
    (sqldir / 'tokenizer' / 'icu_tokenizer.sql').write_text("SELECT 'a'")
    shutil.copy(str(project_env.lib_dir.sql / 'tokenizer' / 'icu_tokenizer_tables.sql'),
                str(sqldir / 'tokenizer' / 'icu_tokenizer_tables.sql'))

    project_env.lib_dir.sql = sqldir

    return project_env


@pytest.fixture
def tokenizer_factory(dsn, tmp_path, property_table,
                      sql_preprocessor, place_table, word_table):
    (tmp_path / 'tokenizer').mkdir()

    def _maker():
        return icu_tokenizer.create(dsn, tmp_path / 'tokenizer')

    return _maker


@pytest.fixture
def db_prop(temp_db_conn):
    def _get_db_property(name):
        return properties.get_property(temp_db_conn, name)

    return _get_db_property


@pytest.fixture
def analyzer(tokenizer_factory, test_config, monkeypatch,
             temp_db_with_extensions, tmp_path):
    sql = tmp_path / 'sql' / 'tokenizer' / 'icu_tokenizer.sql'
    sql.write_text("SELECT 'a';")

    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    def _mk_analyser(norm=("[[:Punctuation:][:Space:]]+ > ' '",), trans=(':: upper()',),
                     variants=('~gasse -> gasse', 'street => st', ),
                     sanitizers=[], with_housenumber=False,
                     with_postcode=False):
        cfgstr = {'normalization': list(norm),
                  'sanitizers': sanitizers,
                  'transliteration': list(trans),
                  'token-analysis': [{'analyzer': 'generic',
                                      'variants': [{'words': list(variants)}]}]}
        if with_housenumber:
            cfgstr['token-analysis'].append({'id': '@housenumber',
                                             'analyzer': 'housenumbers'})
        if with_postcode:
            cfgstr['token-analysis'].append({'id': '@postcode',
                                             'analyzer': 'postcodes'})
        (test_config.project_dir / 'icu_tokenizer.yaml').write_text(yaml.dump(cfgstr))
        tok.loader = nominatim.tokenizer.icu_rule_loader.ICURuleLoader(test_config)

        return tok.name_analyzer()

    return _mk_analyser

@pytest.fixture
def sql_functions(temp_db_conn, def_config, src_dir):
    orig_sql = def_config.lib_dir.sql
    def_config.lib_dir.sql = src_dir / 'lib-sql'
    sqlproc = SQLPreprocessor(temp_db_conn, def_config)
    sqlproc.run_sql_file(temp_db_conn, 'functions/utils.sql')
    sqlproc.run_sql_file(temp_db_conn, 'tokenizer/icu_tokenizer.sql')
    def_config.lib_dir.sql = orig_sql


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
    FROM word WHERE info->>'word' = norm_term and type = 'W';

  IF full_token IS NULL THEN
    full_token := nextval('seq_word');
    INSERT INTO word (word_id, word_token, type, info)
      SELECT full_token, lookup_term, 'W',
             json_build_object('word', norm_term, 'count', 0)
        FROM unnest(lookup_terms) as lookup_term;
  END IF;

  FOR term IN SELECT unnest(string_to_array(unnest(lookup_terms), ' ')) LOOP
    term := trim(term);
    IF NOT (ARRAY[term] <@ partial_terms) THEN
      partial_terms := partial_terms || term;
    END IF;
  END LOOP;

  partial_tokens := '{}'::INT[];
  FOR term IN SELECT unnest(partial_terms) LOOP
    SELECT min(word_id), max(info->>'count') INTO term_id, term_count
      FROM word WHERE word_token = term and type = 'w';

    IF term_id IS NULL THEN
      term_id := nextval('seq_word');
      term_count := 0;
      INSERT INTO word (word_id, word_token, type, info)
        VALUES (term_id, term, 'w', json_build_object('count', term_count));
    END IF;

    IF NOT (ARRAY[term_id] <@ partial_tokens) THEN
      partial_tokens := partial_tokens || term_id;
    END IF;
  END LOOP;
END;
$$
LANGUAGE plpgsql;
                              """)



def test_init_new(tokenizer_factory, test_config, db_prop):
    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert db_prop(nominatim.tokenizer.icu_rule_loader.DBCFG_IMPORT_NORM_RULES) \
            .startswith(':: lower ();')


def test_init_word_table(tokenizer_factory, test_config, place_row, temp_db_cursor):
    place_row(names={'name' : 'Test Area', 'ref' : '52'})
    place_row(names={'name' : 'No Area'})
    place_row(names={'name' : 'Holzstrasse'})

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert temp_db_cursor.table_exists('word')


def test_init_from_project(test_config, tokenizer_factory):
    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    tok = tokenizer_factory()
    tok.init_from_project(test_config)

    assert tok.loader is not None


def test_update_sql_functions(db_prop, temp_db_cursor,
                              tokenizer_factory, test_config, table_factory,
                              monkeypatch):
    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    table_factory('test', 'txt TEXT')

    func_file = test_config.lib_dir.sql / 'tokenizer' / 'icu_tokenizer.sql'
    func_file.write_text("""INSERT INTO test VALUES (1133)""")

    tok.update_sql_functions(test_config)

    test_content = temp_db_cursor.row_set('SELECT * FROM test')
    assert test_content == set((('1133', ), ))


def test_finalize_import(tokenizer_factory, temp_db_conn,
                         temp_db_cursor, test_config, sql_preprocessor_cfg):
    func_file = test_config.lib_dir.sql / 'tokenizer' / 'legacy_tokenizer_indices.sql'
    func_file.write_text("""CREATE FUNCTION test() RETURNS TEXT
                            AS $$ SELECT 'b'::text $$ LANGUAGE SQL""")

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    tok.finalize_import(test_config)

    temp_db_cursor.scalar('SELECT test()') == 'b'


def test_check_database(test_config, tokenizer_factory,
                        temp_db_cursor, sql_preprocessor_cfg):
    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert tok.check_database(test_config) is None


def test_update_statistics_reverse_only(word_table, tokenizer_factory):
    tok = tokenizer_factory()
    tok.update_statistics()


def test_update_statistics(word_table, table_factory, temp_db_cursor, tokenizer_factory):
    word_table.add_full_word(1000, 'hello')
    table_factory('search_name',
                  'place_id BIGINT, name_vector INT[]',
                  [(12, [1000])])
    tok = tokenizer_factory()

    tok.update_statistics()

    assert temp_db_cursor.scalar("""SELECT count(*) FROM word
                                    WHERE type = 'W' and
                                          (info->>'count')::int > 0""") > 0


def test_normalize_postcode(analyzer):
    with analyzer() as anl:
        anl.normalize_postcode('123') == '123'
        anl.normalize_postcode('ab-34 ') == 'AB-34'
        anl.normalize_postcode('38 Б') == '38 Б'


class TestPostcodes:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer, sql_functions):
        sanitizers = [{'step': 'clean-postcodes'}]
        with analyzer(sanitizers=sanitizers, with_postcode=True) as anl:
            self.analyzer = anl
            yield anl


    def process_postcode(self, cc, postcode):
        return self.analyzer.process_place(PlaceInfo({'country_code': cc,
                                                      'address': {'postcode': postcode}}))


    def test_update_postcodes_from_db_empty(self, table_factory, word_table):
        table_factory('location_postcode', 'country_code TEXT, postcode TEXT',
                      content=(('de', '12345'), ('se', '132 34'),
                               ('bm', 'AB23'), ('fr', '12345')))

        self.analyzer.update_postcodes_from_db()

        assert word_table.count() == 5
        assert word_table.get_postcodes() == {'12345', '132 34@132 34', 'AB 23@AB 23'}


    def test_update_postcodes_from_db_ambigious(self, table_factory, word_table):
        table_factory('location_postcode', 'country_code TEXT, postcode TEXT',
                      content=(('in', '123456'), ('sg', '123456')))

        self.analyzer.update_postcodes_from_db()

        assert word_table.count() == 3
        assert word_table.get_postcodes() == {'123456', '123456@123 456'}


    def test_update_postcodes_from_db_add_and_remove(self, table_factory, word_table):
        table_factory('location_postcode', 'country_code TEXT, postcode TEXT',
                      content=(('ch', '1234'), ('bm', 'BC 45'), ('bm', 'XX45')))
        word_table.add_postcode(' 1234', '1234')
        word_table.add_postcode(' 5678', '5678')

        self.analyzer.update_postcodes_from_db()

        assert word_table.count() == 5
        assert word_table.get_postcodes() == {'1234', 'BC 45@BC 45', 'XX 45@XX 45'}


    def test_process_place_postcode_simple(self, word_table):
        info = self.process_postcode('de', '12345')

        assert info['postcode'] == '12345'

        assert word_table.get_postcodes() == {'12345', }


    def test_process_place_postcode_with_space(self, word_table):
        info = self.process_postcode('in', '123 567')

        assert info['postcode'] == '123567'

        assert word_table.get_postcodes() == {'123567@123 567', }



def test_update_special_phrase_empty_table(analyzer, word_table):
    with analyzer() as anl:
        anl.update_special_phrases([
            ("König  bei", "amenity", "royal", "near"),
            ("Könige ", "amenity", "royal", "-"),
            ("street", "highway", "primary", "in")
        ], True)

    assert word_table.get_special() \
               == {('KÖNIG BEI', 'König bei', 'amenity', 'royal', 'near'),
                   ('KÖNIGE', 'Könige', 'amenity', 'royal', None),
                   ('STREET', 'street', 'highway', 'primary', 'in')}


def test_update_special_phrase_delete_all(analyzer, word_table):
    word_table.add_special('FOO', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special('BAR', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    with analyzer() as anl:
        anl.update_special_phrases([], True)

    assert word_table.count_special() == 0


def test_update_special_phrases_no_replace(analyzer, word_table):
    word_table.add_special('FOO', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special('BAR', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    with analyzer() as anl:
        anl.update_special_phrases([], False)

    assert word_table.count_special() == 2


def test_update_special_phrase_modify(analyzer, word_table):
    word_table.add_special('FOO', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special('BAR', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    with analyzer() as anl:
        anl.update_special_phrases([
            ('prison', 'amenity', 'prison', 'in'),
            ('bar', 'highway', 'road', '-'),
            ('garden', 'leisure', 'garden', 'near')
        ], True)

    assert word_table.get_special() \
               == {('PRISON', 'prison', 'amenity', 'prison', 'in'),
                   ('BAR', 'bar', 'highway', 'road', None),
                   ('GARDEN', 'garden', 'leisure', 'garden', 'near')}


def test_add_country_names_new(analyzer, word_table):
    with analyzer() as anl:
        anl.add_country_names('es', {'name': 'Espagña', 'name:en': 'Spain'})

    assert word_table.get_country() == {('es', 'ESPAGÑA'), ('es', 'SPAIN')}


def test_add_country_names_extend(analyzer, word_table):
    word_table.add_country('ch', 'SCHWEIZ')

    with analyzer() as anl:
        anl.add_country_names('ch', {'name': 'Schweiz', 'name:fr': 'Suisse'})

    assert word_table.get_country() == {('ch', 'SCHWEIZ'), ('ch', 'SUISSE')}


class TestPlaceNames:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer, sql_functions):
        sanitizers = [{'step': 'split-name-list'},
                      {'step': 'strip-brace-terms'}]
        with analyzer(sanitizers=sanitizers) as anl:
            self.analyzer = anl
            yield anl


    def expect_name_terms(self, info, *expected_terms):
        tokens = self.analyzer.get_word_token_info(expected_terms)
        for token in tokens:
            assert token[2] is not None, "No token for {0}".format(token)

        assert eval(info['names']) == set((t[2] for t in tokens))


    def process_named_place(self, names):
        return self.analyzer.process_place(PlaceInfo({'name': names}))


    def test_simple_names(self):
        info = self.process_named_place({'name': 'Soft bAr', 'ref': '34'})

        self.expect_name_terms(info, '#Soft bAr', '#34', 'Soft', 'bAr', '34')


    @pytest.mark.parametrize('sep', [',' , ';'])
    def test_names_with_separator(self, sep):
        info = self.process_named_place({'name': sep.join(('New York', 'Big Apple'))})

        self.expect_name_terms(info, '#New York', '#Big Apple',
                                     'new', 'york', 'big', 'apple')


    def test_full_names_with_bracket(self):
        info = self.process_named_place({'name': 'Houseboat (left)'})

        self.expect_name_terms(info, '#Houseboat (left)', '#Houseboat',
                                     'houseboat', 'left')


    def test_country_name(self, word_table):
        place = PlaceInfo({'name' : {'name': 'Norge'},
                           'country_code': 'no',
                           'rank_address': 4,
                           'class': 'boundary',
                           'type': 'administrative'})

        info = self.analyzer.process_place(place)

        self.expect_name_terms(info, '#norge', 'norge')
        assert word_table.get_country() == {('no', 'NORGE')}


class TestPlaceAddress:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer, sql_functions):
        hnr = {'step': 'clean-housenumbers',
               'filter-kind': ['housenumber', 'conscriptionnumber', 'streetnumber']}
        with analyzer(trans=(":: upper()", "'🜵' > ' '"), sanitizers=[hnr]) as anl:
            self.analyzer = anl
            yield anl


    @pytest.fixture
    def getorcreate_hnr_id(self, temp_db_cursor):
        temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_hnr_id(lookup_term TEXT)
                                  RETURNS INTEGER AS $$
                                    SELECT -nextval('seq_word')::INTEGER; $$ LANGUAGE SQL""")


    def process_address(self, **kwargs):
        return self.analyzer.process_place(PlaceInfo({'address': kwargs}))


    def name_token_set(self, *expected_terms):
        tokens = self.analyzer.get_word_token_info(expected_terms)
        for token in tokens:
            assert token[2] is not None, "No token for {0}".format(token)

        return set((t[2] for t in tokens))


    @pytest.mark.parametrize('pcode', ['12345', 'AB 123', '34-345'])
    def test_process_place_postcode(self, word_table, pcode):
        self.process_address(postcode=pcode)

        assert word_table.get_postcodes() == {pcode, }


    @pytest.mark.parametrize('hnr', ['123a', '1', '101'])
    def test_process_place_housenumbers_simple(self, hnr, getorcreate_hnr_id):
        info = self.process_address(housenumber=hnr)

        assert info['hnr'] == hnr.upper()
        assert info['hnr_tokens'] == "{-1}"


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
        self.analyzer.process_place(PlaceInfo({'name': {'name' : 'Grand Road'}}))
        info = self.process_address(street='Grand Road')

        assert eval(info['street']) == self.name_token_set('#Grand Road')


    def test_process_place_nonexisting_street(self):
        info = self.process_address(street='Grand Road')

        assert 'street' not in info


    def test_process_place_multiple_street_tags(self):
        self.analyzer.process_place(PlaceInfo({'name': {'name' : 'Grand Road',
                                                        'ref': '05989'}}))
        info = self.process_address(**{'street': 'Grand Road',
                                      'street:sym_ul': '05989'})

        assert eval(info['street']) == self.name_token_set('#Grand Road', '#05989')


    def test_process_place_street_empty(self):
        info = self.process_address(street='🜵')

        assert 'street' not in info


    def test_process_place_street_from_cache(self):
        self.analyzer.process_place(PlaceInfo({'name': {'name' : 'Grand Road'}}))
        self.process_address(street='Grand Road')

        # request address again
        info = self.process_address(street='Grand Road')

        assert eval(info['street']) == self.name_token_set('#Grand Road')


    def test_process_place_place(self):
        info = self.process_address(place='Honu Lulu')

        assert eval(info['place']) == self.name_token_set('HONU', 'LULU')


    def test_process_place_place_extra(self):
        info = self.process_address(**{'place:en': 'Honu Lulu'})

        assert 'place' not in info


    def test_process_place_place_empty(self):
        info = self.process_address(place='🜵')

        assert 'place' not in info


    def test_process_place_address_terms(self):
        info = self.process_address(country='de', city='Zwickau', state='Sachsen',
                                    suburb='Zwickau', street='Hauptstr',
                                    full='right behind the church')

        city = self.name_token_set('ZWICKAU')
        state = self.name_token_set('SACHSEN')

        result = {k: eval(v) for k,v in info['addr'].items()}

        assert result == {'city': city, 'suburb': city, 'state': state}


    def test_process_place_multiple_address_terms(self):
        info = self.process_address(**{'city': 'Bruxelles', 'city:de': 'Brüssel'})

        result = {k: eval(v) for k,v in info['addr'].items()}

        assert result == {'city': self.name_token_set('Bruxelles')}


    def test_process_place_address_terms_empty(self):
        info = self.process_address(country='de', city=' ', street='Hauptstr',
                                    full='right behind the church')

        assert 'addr' not in info


class TestPlaceHousenumberWithAnalyser:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer, sql_functions):
        hnr = {'step': 'clean-housenumbers',
               'filter-kind': ['housenumber', 'conscriptionnumber', 'streetnumber']}
        with analyzer(trans=(":: upper()", "'🜵' > ' '"), sanitizers=[hnr], with_housenumber=True) as anl:
            self.analyzer = anl
            yield anl


    @pytest.fixture
    def getorcreate_hnr_id(self, temp_db_cursor):
        temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION create_analyzed_hnr_id(norm_term TEXT, lookup_terms TEXT[])
                                  RETURNS INTEGER AS $$
                                    SELECT -nextval('seq_word')::INTEGER; $$ LANGUAGE SQL""")


    def process_address(self, **kwargs):
        return self.analyzer.process_place(PlaceInfo({'address': kwargs}))


    def name_token_set(self, *expected_terms):
        tokens = self.analyzer.get_word_token_info(expected_terms)
        for token in tokens:
            assert token[2] is not None, "No token for {0}".format(token)

        return set((t[2] for t in tokens))


    @pytest.mark.parametrize('hnr', ['123 a', '1', '101'])
    def test_process_place_housenumbers_simple(self, hnr, getorcreate_hnr_id):
        info = self.process_address(housenumber=hnr)

        assert info['hnr'] == hnr.upper()
        assert info['hnr_tokens'] == "{-1}"


    def test_process_place_housenumbers_duplicates(self, getorcreate_hnr_id):
        info = self.process_address(housenumber='134',
                                    conscriptionnumber='134',
                                    streetnumber='99a')

        assert set(info['hnr'].split(';')) == set(('134', '99 A'))
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


class TestUpdateWordTokens:

    @pytest.fixture(autouse=True)
    def setup(self, tokenizer_factory, table_factory, placex_table, word_table):
        table_factory('search_name', 'place_id BIGINT, name_vector INT[]')
        self.tok = tokenizer_factory()


    @pytest.fixture
    def search_entry(self, temp_db_cursor):
        place_id = itertools.count(1000)

        def _insert(*args):
            temp_db_cursor.execute("INSERT INTO search_name VALUES (%s, %s)",
                                   (next(place_id), list(args)))

        return _insert


    @pytest.fixture(params=['simple', 'analyzed'])
    def add_housenumber(self, request, word_table):
        if request.param == 'simple':
            def _make(hid, hnr):
                word_table.add_housenumber(hid, hnr)
        elif request.param == 'analyzed':
            def _make(hid, hnr):
                word_table.add_housenumber(hid, [hnr])

        return _make


    @pytest.mark.parametrize('hnr', ('1a', '1234567', '34 5'))
    def test_remove_unused_housenumbers(self, add_housenumber, word_table, hnr):
        word_table.add_housenumber(1000, hnr)

        assert word_table.count_housenumbers() == 1
        self.tok.update_word_tokens()
        assert word_table.count_housenumbers() == 0


    def test_keep_unused_numeral_housenumbers(self, add_housenumber, word_table):
        add_housenumber(1000, '5432')

        assert word_table.count_housenumbers() == 1
        self.tok.update_word_tokens()
        assert word_table.count_housenumbers() == 1


    def test_keep_housenumbers_from_search_name_table(self, add_housenumber, word_table, search_entry):
        add_housenumber(9999, '5432a')
        add_housenumber(9991, '9 a')
        search_entry(123, 9999, 34)

        assert word_table.count_housenumbers() == 2
        self.tok.update_word_tokens()
        assert word_table.count_housenumbers() == 1


    def test_keep_housenumbers_from_placex_table(self, add_housenumber, word_table, placex_table):
        add_housenumber(9999, '5432a')
        add_housenumber(9990, '34z')
        placex_table.add(housenumber='34z')
        placex_table.add(housenumber='25432a')

        assert word_table.count_housenumbers() == 2
        self.tok.update_word_tokens()
        assert word_table.count_housenumbers() == 1


    def test_keep_housenumbers_from_placex_table_hnr_list(self, add_housenumber, word_table, placex_table):
        add_housenumber(9991, '9 b')
        add_housenumber(9990, '34z')
        placex_table.add(housenumber='9 a;9 b;9 c')

        assert word_table.count_housenumbers() == 2
        self.tok.update_word_tokens()
        assert word_table.count_housenumbers() == 1
