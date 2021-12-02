"""
Test for legacy tokenizer.
"""
import shutil
import re

import pytest

from nominatim.indexer.place_info import PlaceInfo
from nominatim.tokenizer import legacy_tokenizer
from nominatim.db import properties
from nominatim.errors import UsageError

from mock_legacy_word_table import MockLegacyWordTable

# Force use of legacy word table
@pytest.fixture
def word_table(temp_db_conn):
    return MockLegacyWordTable(temp_db_conn)


@pytest.fixture
def test_config(project_env, tmp_path):
    module_dir = tmp_path / 'module_src'
    module_dir.mkdir()
    (module_dir / 'nominatim.so').write_text('TEST nomiantim.so')

    project_env.lib_dir.module = module_dir

    sqldir = tmp_path / 'sql'
    sqldir.mkdir()
    (sqldir / 'tokenizer').mkdir()

    # Get the original SQL but replace make_standard_name to avoid module use.
    init_sql = (project_env.lib_dir.sql / 'tokenizer' / 'legacy_tokenizer.sql').read_text()
    for fn in ('transliteration', 'gettokenstring'):
        init_sql = re.sub(f'CREATE OR REPLACE FUNCTION {fn}[^;]*;',
                          '', init_sql, re.DOTALL)
    init_sql += """
                   CREATE OR REPLACE FUNCTION make_standard_name(name TEXT)
                   RETURNS TEXT AS $$ SELECT lower(name); $$ LANGUAGE SQL;

                """
    # Also load util functions. Some are needed by the tokenizer.
    init_sql += (project_env.lib_dir.sql / 'functions' / 'utils.sql').read_text()
    (sqldir / 'tokenizer' / 'legacy_tokenizer.sql').write_text(init_sql)

    (sqldir / 'words.sql').write_text("SELECT 'a'")

    shutil.copy(str(project_env.lib_dir.sql / 'tokenizer' / 'legacy_tokenizer_tables.sql'),
                str(sqldir / 'tokenizer' / 'legacy_tokenizer_tables.sql'))

    project_env.lib_dir.sql = sqldir
    project_env.lib_dir.data = sqldir

    return project_env


@pytest.fixture
def tokenizer_factory(dsn, tmp_path, property_table):
    (tmp_path / 'tokenizer').mkdir()

    def _maker():
        return legacy_tokenizer.create(dsn, tmp_path / 'tokenizer')

    return _maker


@pytest.fixture
def tokenizer_setup(tokenizer_factory, test_config, monkeypatch, sql_preprocessor):
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)
    tok = tokenizer_factory()
    tok.init_new_db(test_config)


@pytest.fixture
def analyzer(tokenizer_factory, test_config, monkeypatch, sql_preprocessor,
             word_table, temp_db_with_extensions, tmp_path):
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', ':: lower();')
    tok = tokenizer_factory()
    tok.init_new_db(test_config)
    monkeypatch.undo()

    with tok.name_analyzer() as analyzer:
        yield analyzer


@pytest.fixture
def make_standard_name(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION make_standard_name(name TEXT)
                              RETURNS TEXT AS $$ SELECT '#' || lower(name) || '#'; $$ LANGUAGE SQL""")


@pytest.fixture
def create_postcode_id(temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION create_postcode_id(postcode TEXT)
                              RETURNS BOOLEAN AS $$
                              INSERT INTO word (word_token, word, class, type)
                                VALUES (' ' || postcode, postcode, 'place', 'postcode')
                              RETURNING True;
                              $$ LANGUAGE SQL""")


def test_init_new(tokenizer_factory, test_config, monkeypatch,
                  temp_db_conn, sql_preprocessor):
    monkeypatch.setenv('NOMINATIM_TERM_NORMALIZATION', 'xxvv')
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_NORMALIZATION) == 'xxvv'

    outfile = test_config.project_dir / 'module' / 'nominatim.so'

    assert outfile.exists()
    assert outfile.read_text() == 'TEST nomiantim.so'
    assert outfile.stat().st_mode == 33261


def test_init_module_load_failed(tokenizer_factory, test_config):
    tok = tokenizer_factory()

    with pytest.raises(UsageError):
        tok.init_new_db(test_config)


def test_init_module_custom(tokenizer_factory, test_config,
                            monkeypatch, tmp_path, sql_preprocessor):
    module_dir = (tmp_path / 'custom').resolve()
    module_dir.mkdir()
    (module_dir/ 'nominatim.so').write_text('CUSTOM nomiantim.so')

    monkeypatch.setenv('NOMINATIM_DATABASE_MODULE_PATH', str(module_dir))
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert not (test_config.project_dir / 'module').exists()


def test_init_from_project(tokenizer_setup, tokenizer_factory, test_config):
    tok = tokenizer_factory()

    tok.init_from_project(test_config)

    assert tok.normalization is not None


def test_update_sql_functions(sql_preprocessor, temp_db_conn,
                              tokenizer_factory, test_config, table_factory,
                              monkeypatch, temp_db_cursor):
    monkeypatch.setenv('NOMINATIM_MAX_WORD_FREQUENCY', '1133')
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)
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


def test_finalize_import(tokenizer_factory, temp_db_conn,
                         temp_db_cursor, test_config, monkeypatch,
                         sql_preprocessor_cfg):
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)

    func_file = test_config.lib_dir.sql / 'tokenizer' / 'legacy_tokenizer_indices.sql'
    func_file.write_text("""CREATE FUNCTION test() RETURNS TEXT
                            AS $$ SELECT 'b' $$ LANGUAGE SQL""")

    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    tok.finalize_import(test_config)

    temp_db_cursor.scalar('SELECT test()') == 'b'


def test_migrate_database(tokenizer_factory, test_config, temp_db_conn, monkeypatch):
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)
    tok = tokenizer_factory()
    tok.migrate_database(test_config)

    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_MAXWORDFREQ) is not None
    assert properties.get_property(temp_db_conn, legacy_tokenizer.DBCFG_NORMALIZATION) is not None

    outfile = test_config.project_dir / 'module' / 'nominatim.so'

    assert outfile.exists()
    assert outfile.read_text() == 'TEST nomiantim.so'
    assert outfile.stat().st_mode == 33261


def test_check_database(test_config, tokenizer_factory, monkeypatch,
                        temp_db_cursor, sql_preprocessor_cfg):
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)
    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    assert tok.check_database(False) is None


def test_check_database_no_tokenizer(test_config, tokenizer_factory):
    tok = tokenizer_factory()

    assert tok.check_database(False) is not None


def test_check_database_bad_setup(test_config, tokenizer_factory, monkeypatch,
                                  temp_db_cursor, sql_preprocessor_cfg):
    monkeypatch.setattr(legacy_tokenizer, '_check_module', lambda m, c: None)
    tok = tokenizer_factory()
    tok.init_new_db(test_config)

    # Inject a bad transliteration.
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION make_standard_name(name TEXT)
                              RETURNS TEXT AS $$ SELECT 'garbage'; $$ LANGUAGE SQL""")

    assert tok.check_database(False) is not None


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
                                    WHERE word_token like ' %' and
                                          search_name_count > 0""") > 0


def test_normalize(analyzer):
    assert analyzer.normalize('TEsT') == 'test'


def test_update_postcodes_from_db_empty(analyzer, table_factory, word_table,
                                        create_postcode_id):
    table_factory('location_postcode', 'postcode TEXT',
                  content=(('1234',), ('12 34',), ('AB23',), ('1234',)))

    analyzer.update_postcodes_from_db()

    assert word_table.get_postcodes() == {'1234', '12 34', 'AB23'}


def test_update_postcodes_from_db_add_and_remove(analyzer, table_factory, word_table,
                                                 create_postcode_id):
    table_factory('location_postcode', 'postcode TEXT',
                  content=(('1234',), ('45BC', ), ('XX45', )))
    word_table.add_postcode(' 1234', '1234')
    word_table.add_postcode(' 5678', '5678')

    analyzer.update_postcodes_from_db()

    assert word_table.get_postcodes() == {'1234', '45BC', 'XX45'}


def test_update_special_phrase_empty_table(analyzer, word_table, make_standard_name):
    analyzer.update_special_phrases([
        ("König bei", "amenity", "royal", "near"),
        ("Könige", "amenity", "royal", "-"),
        ("könige", "amenity", "royal", "-"),
        ("strasse", "highway", "primary", "in")
    ], True)

    assert word_table.get_special() \
               == set(((' #könig bei#', 'könig bei', 'amenity', 'royal', 'near'),
                       (' #könige#', 'könige', 'amenity', 'royal', None),
                       (' #strasse#', 'strasse', 'highway', 'primary', 'in')))


def test_update_special_phrase_delete_all(analyzer, word_table, make_standard_name):
    word_table.add_special(' #foo#', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' #bar#', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    analyzer.update_special_phrases([], True)

    assert word_table.count_special() == 0


def test_update_special_phrases_no_replace(analyzer, word_table, make_standard_name):
    word_table.add_special(' #foo#', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' #bar#', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    analyzer.update_special_phrases([], False)

    assert word_table.count_special() == 2


def test_update_special_phrase_modify(analyzer, word_table, make_standard_name):
    word_table.add_special(' #foo#', 'foo', 'amenity', 'prison', 'in')
    word_table.add_special(' #bar#', 'bar', 'highway', 'road', None)

    assert word_table.count_special() == 2

    analyzer.update_special_phrases([
        ('prison', 'amenity', 'prison', 'in'),
        ('bar', 'highway', 'road', '-'),
        ('garden', 'leisure', 'garden', 'near')
    ], True)

    assert word_table.get_special() \
               == set(((' #prison#', 'prison', 'amenity', 'prison', 'in'),
                       (' #bar#', 'bar', 'highway', 'road', None),
                       (' #garden#', 'garden', 'leisure', 'garden', 'near')))


def test_add_country_names(analyzer, word_table, make_standard_name):
    analyzer.add_country_names('de', {'name': 'Germany',
                                      'name:de': 'Deutschland',
                                      'short_name': 'germany'})

    assert word_table.get_country() \
               == {('de', ' #germany#'),
                   ('de', ' #deutschland#')}


def test_add_more_country_names(analyzer, word_table, make_standard_name):
    word_table.add_country('fr', ' #france#')
    word_table.add_country('it', ' #italy#')
    word_table.add_country('it', ' #itala#')

    analyzer.add_country_names('it', {'name': 'Italy', 'ref': 'IT'})

    assert word_table.get_country() \
               == {('fr', ' #france#'),
                   ('it', ' #italy#'),
                   ('it', ' #itala#'),
                   ('it', ' #it#')}


@pytest.mark.parametrize('pcode', ['12345', 'AB 123', '34-345'])
def test_process_place_postcode(analyzer, create_postcode_id, word_table, pcode):
    analyzer.process_place(PlaceInfo({'address': {'postcode' : pcode}}))

    assert word_table.get_postcodes() == {pcode, }


@pytest.mark.parametrize('pcode', ['12:23', 'ab;cd;f', '123;836'])
def test_process_place_bad_postcode(analyzer, create_postcode_id, word_table, pcode):
    analyzer.process_place(PlaceInfo({'address': {'postcode' : pcode}}))

    assert not word_table.get_postcodes()


class TestHousenumberName:

    @staticmethod
    @pytest.fixture(autouse=True)
    def setup_create_housenumbers(temp_db_cursor):
        temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION create_housenumbers(
                                      housenumbers TEXT[],
                                      OUT tokens TEXT, OUT normtext TEXT)
                                  AS $$
                                  SELECT housenumbers::TEXT, array_to_string(housenumbers, ';')
                                  $$ LANGUAGE SQL""")


    @staticmethod
    @pytest.mark.parametrize('hnr', ['123a', '1', '101'])
    def test_process_place_housenumbers_simple(analyzer, hnr):
        info = analyzer.process_place(PlaceInfo({'address': {'housenumber' : hnr}}))

        assert info['hnr'] == hnr
        assert info['hnr_tokens'].startswith("{")


    @staticmethod
    def test_process_place_housenumbers_lists(analyzer):
        info = analyzer.process_place(PlaceInfo({'address': {'conscriptionnumber' : '1; 2;3'}}))

        assert set(info['hnr'].split(';')) == set(('1', '2', '3'))


    @staticmethod
    def test_process_place_housenumbers_duplicates(analyzer):
        info = analyzer.process_place(PlaceInfo({'address': {'housenumber' : '134',
                                                   'conscriptionnumber' : '134',
                                                   'streetnumber' : '99a'}}))

        assert set(info['hnr'].split(';')) == set(('134', '99a'))


class TestPlaceNames:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer):
        self.analyzer = analyzer


    def expect_name_terms(self, info, *expected_terms):
        tokens = self.analyzer.get_word_token_info(list(expected_terms))
        for token in tokens:
            assert token[2] is not None, "No token for {0}".format(token)

        assert eval(info['names']) == set((t[2] for t in tokens)),\
               f"Expected: {tokens}\nGot: {info['names']}"


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
                                     'houseboat', '(left)')


    def test_country_name(self, word_table):
        place = PlaceInfo({'name' : {'name': 'Norge'},
                           'country_code': 'no',
                           'rank_address': 4,
                           'class': 'boundary',
                           'type': 'administrative'})

        info = self.analyzer.process_place(place)

        self.expect_name_terms(info, '#norge', 'norge')
        assert word_table.get_country() == {('no', ' norge')}


class TestPlaceAddress:

    @pytest.fixture(autouse=True)
    def setup(self, analyzer):
        self.analyzer = analyzer


    @pytest.fixture
    def getorcreate_hnr_id(self, temp_db_cursor):
        temp_db_cursor.execute("""CREATE SEQUENCE seq_hnr start 1;
                                  CREATE OR REPLACE FUNCTION getorcreate_housenumber_id(lookup_word TEXT)
                                  RETURNS INTEGER AS $$
                                  SELECT -nextval('seq_hnr')::INTEGER; $$ LANGUAGE SQL""")

    def process_address(self, **kwargs):
        return self.analyzer.process_place(PlaceInfo({'address': kwargs}))


    def name_token_set(self, *expected_terms):
        tokens = self.analyzer.get_word_token_info(list(expected_terms))
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


    @pytest.mark.parametrize('hnr', ['123a', '0', '101'])
    def test_process_place_housenumbers_simple(self, hnr, getorcreate_hnr_id):
        info = self.process_address(housenumber=hnr)

        assert info['hnr'] == hnr.lower()
        assert info['hnr_tokens'] == "{-1}"


    def test_process_place_housenumbers_lists(self, getorcreate_hnr_id):
        info = self.process_address(conscriptionnumber='1; 2;3')

        assert set(info['hnr'].split(';')) == set(('1', '2', '3'))
        assert info['hnr_tokens'] == "{-1,-2,-3}"


    def test_process_place_housenumbers_duplicates(self, getorcreate_hnr_id):
        info = self.process_address(housenumber='134',
                                    conscriptionnumber='134',
                                    streetnumber='99A')

        assert set(info['hnr'].split(';')) == set(('134', '99a'))
        assert info['hnr_tokens'] == "{-1,-2}"


    def test_process_place_street(self):
        # legacy tokenizer only indexes known names
        self.analyzer.process_place(PlaceInfo({'name': {'name' : 'Grand Road'}}))
        info = self.process_address(street='Grand Road')

        assert eval(info['street']) == self.name_token_set('#Grand Road')


    def test_process_place_street_empty(self):
        info = self.process_address(street='🜵')

        assert 'street' not in info


    def test_process_place_place(self):
        self.analyzer.process_place(PlaceInfo({'name': {'name' : 'Honu Lulu'}}))
        info = self.process_address(place='Honu Lulu')

        assert eval(info['place_search']) == self.name_token_set('#Honu Lulu',
                                                                 'Honu', 'Lulu')
        assert eval(info['place_match']) == self.name_token_set('#Honu Lulu')


    def test_process_place_place_empty(self):
        info = self.process_address(place='🜵')

        assert 'place' not in info


    def test_process_place_address_terms(self):
        for name in ('Zwickau', 'Haupstraße', 'Sachsen'):
            self.analyzer.process_place(PlaceInfo({'name': {'name' : name}}))
        info = self.process_address(country='de', city='Zwickau', state='Sachsen',
                                    suburb='Zwickau', street='Hauptstr',
                                    full='right behind the church')

        city = self.name_token_set('ZWICKAU')
        state = self.name_token_set('SACHSEN')

        print(info)
        result = {k: eval(v[0]) for k,v in info['addr'].items()}

        assert result == {'city': city, 'suburb': city, 'state': state}


    def test_process_place_address_terms_empty(self):
        info = self.process_address(country='de', city=' ', street='Hauptstr',
                                    full='right behind the church')

        assert 'addr' not in info

