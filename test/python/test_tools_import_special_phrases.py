"""
    Tests for import special phrases functions
"""
import pytest
from nominatim.tools.special_phrases import _create_place_classtype_indexes, _create_place_classtype_table, _get_wiki_content, _grant_access_to_webuser, _process_amenity

def test_get_wiki_content():
    assert _get_wiki_content('fr')

def execute_and_verify_add_word(temp_db_conn, phrase_label, phrase_class, phrase_type):
    _process_amenity(temp_db_conn, phrase_label, phrase_class, phrase_type, '')

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute(f"""
            SELECT * FROM word 
            WHERE word_token=' {phrase_label}'
            AND word='{phrase_label}'
            AND class='{phrase_class}'
            AND type='{phrase_type}'""")
        return temp_db_cursor.fetchone()

def execute_and_verify_add_word_with_operator(temp_db_conn, phrase_label, phrase_class, phrase_type, phrase_operator):
    _process_amenity(temp_db_conn, phrase_label, phrase_class, phrase_type, phrase_operator)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute(f"""
            SELECT * FROM word 
            WHERE word_token=' {phrase_label}'
            AND word='{phrase_label}'
            AND class='{phrase_class}'
            AND type='{phrase_type}'
            AND operator='{phrase_operator}'""")
        return temp_db_cursor.fetchone()

def test_process_amenity_with_near_operator(temp_db_conn, word_table, amenity_operator_funcs):
    phrase_label = 'label'
    phrase_class = 'class'
    phrase_type = 'type'

    assert execute_and_verify_add_word(temp_db_conn, phrase_label, phrase_class, phrase_type)
    assert execute_and_verify_add_word_with_operator(temp_db_conn, phrase_label, phrase_class, phrase_type, 'near')
    assert execute_and_verify_add_word_with_operator(temp_db_conn, phrase_label, phrase_class, phrase_type, 'in')

def index_exists(db_connect, index):
        """ Check that an index with the given name exists in the database.
        """
        with db_connect.cursor() as cur:
            cur.execute("""SELECT tablename FROM pg_indexes
                           WHERE indexname = %s and schemaname = 'public'""", (index, ))
            if cur.rowcount == 0:
                return False
        return True

def test_create_place_classtype_indexes(temp_db_conn):
    phrase_class = 'class'
    phrase_type = 'type'
    table_name = f'place_classtype_{phrase_class}_{phrase_type}'

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute("CREATE EXTENSION postgis;")
        temp_db_cursor.execute(f'CREATE TABLE {table_name}(place_id BIGINT, centroid GEOMETRY)')

    _create_place_classtype_indexes(temp_db_conn, '', phrase_class, phrase_type)

    centroid_index_exists = index_exists(temp_db_conn, f'idx_place_classtype_{phrase_class}_{phrase_type}_centroid')
    place_id_index_exists = index_exists(temp_db_conn, f'idx_place_classtype_{phrase_class}_{phrase_type}_place_id')

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
    table_name = f'place_classtype_{phrase_class}_{phrase_type}'

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute(f'CREATE TABLE {table_name}()')

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
def amenity_operator_funcs(temp_db_cursor):                        
    temp_db_cursor.execute(f"""
        CREATE OR REPLACE FUNCTION make_standard_name(name TEXT) RETURNS TEXT
        AS $$
        DECLARE
        o TEXT;
        BEGIN
        RETURN name; --Basically return the same name for the tests
        END;
        $$
        LANGUAGE plpgsql IMMUTABLE;

        CREATE SEQUENCE seq_word start 1;

        CREATE OR REPLACE FUNCTION getorcreate_amenity(lookup_word TEXT,
                                                    lookup_class text, lookup_type text)
        RETURNS INTEGER
        AS $$
        DECLARE
        lookup_token TEXT;
        return_word_id INTEGER;
        BEGIN
        lookup_token := ' '||trim(lookup_word);
        SELECT min(word_id) FROM word
        WHERE word_token = lookup_token and word = lookup_word
                and class = lookup_class and type = lookup_type
        INTO return_word_id;
        IF return_word_id IS NULL THEN
            return_word_id := nextval('seq_word');
            INSERT INTO word VALUES (return_word_id, lookup_token, lookup_word,
                                    lookup_class, lookup_type, null, 0);
        END IF;
        RETURN return_word_id;
        END;
        $$
        LANGUAGE plpgsql;
        
        CREATE OR REPLACE FUNCTION getorcreate_amenityoperator(lookup_word TEXT,
                                                        lookup_class text,
                                                        lookup_type text,
                                                        op text)
        RETURNS INTEGER
        AS $$
        DECLARE
        lookup_token TEXT;
        return_word_id INTEGER;
        BEGIN
        lookup_token := ' '||trim(lookup_word);
        SELECT min(word_id) FROM word
        WHERE word_token = lookup_token and word = lookup_word
                and class = lookup_class and type = lookup_type and operator = op
        INTO return_word_id;
        IF return_word_id IS NULL THEN
            return_word_id := nextval('seq_word');
            INSERT INTO word VALUES (return_word_id, lookup_token, lookup_word,
                                    lookup_class, lookup_type, null, 0, op);
        END IF;
        RETURN return_word_id;
        END;
        $$
        LANGUAGE plpgsql;""")
