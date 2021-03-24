"""
    Tests for import special phrases functions
"""
from pathlib import Path
import pytest
from nominatim.tools.special_phrases import SpecialPhrasesImporter

TEST_BASE_DIR = Path(__file__) / '..' / '..'

def test_process_amenity_with_operator(special_phrases_importer, getorcreate_amenityoperator_funcs):
    special_phrases_importer._process_amenity('', '', '', '', 'near')
    special_phrases_importer._process_amenity('', '', '', '', 'in')

def test_process_amenity_without_operator(special_phrases_importer, getorcreate_amenity_funcs):
    special_phrases_importer._process_amenity('', '', '', '', '')

def test_create_place_classtype_indexes(temp_db_conn, special_phrases_importer):
    phrase_class = 'class'
    phrase_type = 'type'
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)
    index_prefix = 'idx_place_classtype_{}_{}_'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute("CREATE EXTENSION postgis;")
        temp_db_cursor.execute('CREATE TABLE {}(place_id BIGINT, centroid GEOMETRY)'.format(table_name))

    special_phrases_importer._create_place_classtype_indexes('', phrase_class, phrase_type)

    centroid_index_exists = temp_db_conn.index_exists(index_prefix + 'centroid')
    place_id_index_exists = temp_db_conn.index_exists(index_prefix + 'place_id')

    assert centroid_index_exists and place_id_index_exists

def test_create_place_classtype_table(temp_db_conn, placex_table, special_phrases_importer):
    phrase_class = 'class'
    phrase_type = 'type'
    special_phrases_importer._create_place_classtype_table('', phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute(f"""
            SELECT *
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
            AND table_name='place_classtype_{phrase_class}_{phrase_type}'""")
        result = temp_db_cursor.fetchone()
    assert result

def test_grant_access_to_web_user(temp_db_conn, def_config, special_phrases_importer):
    phrase_class = 'class'
    phrase_type = 'type'
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute('CREATE TABLE {}()'.format(table_name))

    special_phrases_importer._grant_access_to_webuser(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute(f"""
                SELECT * FROM information_schema.role_table_grants
                WHERE table_name='{table_name}' 
                AND grantee='{def_config.DATABASE_WEBUSER}' 
                AND privilege_type='SELECT'""")
        result = temp_db_cursor.fetchone()
    assert result

def test_create_place_classtype_table_and_indexes(
        placex_table, getorcreate_amenity_funcs, 
        getorcreate_amenityoperator_funcs, special_phrases_importer):
    pairs = {('class1', 'type1'), ('class2', 'type2')}

    special_phrases_importer._create_place_classtype_table_and_indexes(pairs)

def test_process_xml_content(special_phrases_importer, getorcreate_amenity_funcs,
                             getorcreate_amenityoperator_funcs):
    special_phrases_importer._process_xml_content(get_test_xml_wiki_content(), 'en')

def mock_get_wiki_content(lang):
    return get_test_xml_wiki_content()

def test_import_from_wiki(monkeypatch, special_phrases_importer, placex_table, 
                          getorcreate_amenity_funcs, getorcreate_amenityoperator_funcs):
    #mocker.patch.object(special_phrases_importer, '_get_wiki_content', new=mock_get_wiki_content)
    monkeypatch.setattr('nominatim.tools.special_phrases.SpecialPhrasesImporter._get_wiki_content', mock_get_wiki_content)
    special_phrases_importer.import_from_wiki(['en'])

def get_test_xml_wiki_content():
    xml_test_content_path = (TEST_BASE_DIR / 'testdata' / 'special_phrases_test_content.txt').resolve()
    with open(xml_test_content_path) as xml_content_reader:
        return xml_content_reader.read()

@pytest.fixture
def special_phrases_importer(temp_db_conn, def_config, tmp_phplib_dir):
    return SpecialPhrasesImporter(def_config, tmp_phplib_dir, temp_db_conn)

@pytest.fixture
def make_strandard_name_func(temp_db_cursor):
    temp_db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION make_standard_name(name TEXT) RETURNS TEXT AS $$
        BEGIN
        RETURN trim(name); --Basically return only the trimed name for the tests
        END;
        $$ LANGUAGE plpgsql IMMUTABLE;""")
        
@pytest.fixture
def getorcreate_amenity_funcs(temp_db_cursor, make_strandard_name_func):
    temp_db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION getorcreate_amenity(lookup_word TEXT, normalized_word TEXT,
                                                    lookup_class text, lookup_type text)
        RETURNS void as $$
        BEGIN END;
        $$ LANGUAGE plpgsql""")

@pytest.fixture
def getorcreate_amenityoperator_funcs(temp_db_cursor, make_strandard_name_func):
    temp_db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION getorcreate_amenityoperator(lookup_word TEXT, normalized_word TEXT,
                                                    lookup_class text, lookup_type text, op text)
        RETURNS void as $$
        BEGIN END;
        $$ LANGUAGE plpgsql""")