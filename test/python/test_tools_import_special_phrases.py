"""
    Tests for import special phrases functions
"""
import pytest
from nominatim.tools.special_phrases import _create_place_classtype_indexes, _create_place_classtype_table, _get_wiki_content, _grant_access_to_webuser, _process_amenity

def test_process_amenity_with_operator(temp_db_conn, getorcreate_amenityoperator_funcs):
    _process_amenity(temp_db_conn, '', '', '', '', 'near')
    _process_amenity(temp_db_conn, '', '', '', '', 'in')

def test_process_amenity_without_operator(temp_db_conn, getorcreate_amenity_funcs):
    _process_amenity(temp_db_conn, '', '', '', '', '')

def test_create_place_classtype_indexes(temp_db_conn):
    phrase_class = 'class'
    phrase_type = 'type'
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)
    index_prefix = 'idx_place_classtype_{}_{}_'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute("CREATE EXTENSION postgis;")
        temp_db_cursor.execute('CREATE TABLE {}(place_id BIGINT, centroid GEOMETRY)'.format(table_name))

    _create_place_classtype_indexes(temp_db_conn, '', phrase_class, phrase_type)

    centroid_index_exists = temp_db_conn.index_exists(index_prefix + 'centroid')
    place_id_index_exists = temp_db_conn.index_exists(index_prefix + 'place_id')

    assert centroid_index_exists and place_id_index_exists

def test_create_place_classtype_table(temp_db_conn, placex_table):
    phrase_class = 'class'
    phrase_type = 'type'
    _create_place_classtype_table(temp_db_conn, '', phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute(f"""
            SELECT *
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
            AND table_name='place_classtype_{phrase_class}_{phrase_type}'""")
        result = temp_db_cursor.fetchone()
    assert result

def test_grant_access_to_web_user(temp_db_conn, def_config):
    phrase_class = 'class'
    phrase_type = 'type'
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute('CREATE TABLE {}()'.format(table_name))

    _grant_access_to_webuser(temp_db_conn, def_config, phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute(f"""
                SELECT * FROM information_schema.role_table_grants
                WHERE table_name='{table_name}' 
                AND grantee='{def_config.DATABASE_WEBUSER}' 
                AND privilege_type='SELECT'""")
        result = temp_db_cursor.fetchone()
    assert result

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