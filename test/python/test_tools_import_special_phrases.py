"""
    Tests for import special phrases methods
    of the class SpecialPhrasesImporter.
"""
from nominatim.errors import UsageError
from pathlib import Path
import tempfile
from shutil import copyfile
import pytest
from nominatim.tools import SpecialPhrasesImporter

TEST_BASE_DIR = Path(__file__) / '..' / '..'

def test_fetch_existing_place_classtype_tables(special_phrases_importer, temp_db_cursor):
    """
        Check for the fetch_existing_place_classtype_tables() method.
        It should return the table just created.
    """
    temp_db_cursor.execute('CREATE TABLE place_classtype_testclasstypetable()')

    special_phrases_importer._fetch_existing_place_classtype_tables()
    contained_table = special_phrases_importer.table_phrases_to_delete.pop()
    assert contained_table == 'place_classtype_testclasstypetable'

def test_check_sanity_class(special_phrases_importer):
    """
        Check for _check_sanity() method.
        If a wrong class or type is given, an UsageError should raise.
        If a good class and type are given, nothing special happens.
    """
    
    assert not special_phrases_importer._check_sanity('en', '', 'type')
    assert not special_phrases_importer._check_sanity('en', 'class', '')

    assert special_phrases_importer._check_sanity('en', 'class', 'type')

def test_load_white_and_black_lists(special_phrases_importer):
    """
        Test that _load_white_and_black_lists() well return
        black list and white list and that they are of dict type.
    """
    black_list, white_list = special_phrases_importer._load_white_and_black_lists()

    assert isinstance(black_list, dict) and isinstance(white_list, dict)

def test_convert_php_settings(special_phrases_importer):
    """
        Test that _convert_php_settings_if_needed() convert the given
        php file to a json file.
    """
    php_file = (TEST_BASE_DIR / 'testfiles' / 'phrase_settings.php').resolve()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_settings = (Path(temp_dir) / 'phrase_settings.php').resolve()
        copyfile(php_file, temp_settings)
        special_phrases_importer._convert_php_settings_if_needed(temp_settings)

        assert (Path(temp_dir) / 'phrase_settings.json').is_file()

def test_convert_settings_wrong_file(special_phrases_importer):
    """
        Test that _convert_php_settings_if_needed() raise an exception
        if the given file is not a valid file.
    """
    with pytest.raises(UsageError, match='random_file is not a valid file.'):
        special_phrases_importer._convert_php_settings_if_needed('random_file')

def test_convert_settings_json_already_exist(special_phrases_importer):
    """
        Test that if we give to '_convert_php_settings_if_needed' a php file path
        and that a the corresponding json file already exists, it is returned.
    """
    php_file = (TEST_BASE_DIR / 'testfiles' / 'phrase_settings.php').resolve()
    json_file = (TEST_BASE_DIR / 'testfiles' / 'phrase_settings.json').resolve()

    returned = special_phrases_importer._convert_php_settings_if_needed(php_file)

    assert returned == json_file

def test_convert_settings_giving_json(special_phrases_importer):
    """
        Test that if we give to '_convert_php_settings_if_needed' a json file path
        the same path is directly returned
    """
    json_file = (TEST_BASE_DIR / 'testfiles' / 'phrase_settings.json').resolve()

    returned = special_phrases_importer._convert_php_settings_if_needed(json_file)

    assert returned == json_file

def test_create_place_classtype_indexes(temp_db_conn, special_phrases_importer):
    """
        Test that _create_place_classtype_indexes() create the
        place_id index and centroid index on the right place_class_type table.
    """
    phrase_class = 'class'
    phrase_type = 'type'
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute("CREATE EXTENSION postgis;")
        temp_db_cursor.execute('CREATE TABLE {}(place_id BIGINT, centroid GEOMETRY)'.format(table_name))

    special_phrases_importer._create_place_classtype_indexes('', phrase_class, phrase_type)

    assert check_placeid_and_centroid_indexes(temp_db_conn, phrase_class, phrase_type)

def test_create_place_classtype_table(temp_db_conn, placex_table, special_phrases_importer):
    """
        Test that _create_place_classtype_table() create
        the right place_classtype table.
    """
    phrase_class = 'class'
    phrase_type = 'type'
    special_phrases_importer._create_place_classtype_table('', phrase_class, phrase_type)

    assert check_table_exist(temp_db_conn, phrase_class, phrase_type)

def test_grant_access_to_web_user(temp_db_conn, def_config, special_phrases_importer):
    """
        Test that _grant_access_to_webuser() give 
        right access to the web user.
    """
    phrase_class = 'class'
    phrase_type = 'type'
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute('CREATE TABLE {}()'.format(table_name))

    special_phrases_importer._grant_access_to_webuser(phrase_class, phrase_type)

    assert check_grant_access(temp_db_conn, def_config.DATABASE_WEBUSER, phrase_class, phrase_type)

def test_create_place_classtype_table_and_indexes(
        temp_db_conn, def_config, placex_table,
        special_phrases_importer):
    """
        Test that _create_place_classtype_table_and_indexes()
        create the right place_classtype tables and place_id indexes
        and centroid indexes and grant access to the web user
        for the given set of pairs.
    """
    pairs = set([('class1', 'type1'), ('class2', 'type2')])

    special_phrases_importer._create_place_classtype_table_and_indexes(pairs)

    for pair in pairs:
        assert check_table_exist(temp_db_conn, pair[0], pair[1])
        assert check_placeid_and_centroid_indexes(temp_db_conn, pair[0], pair[1])
        assert check_grant_access(temp_db_conn, def_config.DATABASE_WEBUSER, pair[0], pair[1])

def test_process_xml_content(temp_db_conn, def_config, special_phrases_importer):
    """
        Test that _process_xml_content() process the given xml content right
        by executing the right SQL functions for amenities and 
        by returning the right set of pairs.
    """
    class_test = 'aerialway'
    type_test = 'zip_line'

    #Converted output set to a dict for easy assert further.
    results = dict(special_phrases_importer._process_xml_content(get_test_xml_wiki_content(), 'en'))

    assert results[class_test] and type_test in results.values()

def test_remove_non_existent_tables_from_db(special_phrases_importer, default_phrases,
                                             temp_db_conn):
    """
        Check for the remove_non_existent_phrases_from_db() method.

        It should removed entries from the word table which are contained
        in the words_phrases_to_delete set and not those also contained
        in the words_phrases_still_exist set.

        place_classtype tables contained in table_phrases_to_delete should
        be deleted.
    """
    with temp_db_conn.cursor() as temp_db_cursor:
        special_phrases_importer.table_phrases_to_delete = {
            'place_classtype_testclasstypetable_to_delete'
        }

        query_tables = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            AND table_name like 'place_classtype_%';
        """

        special_phrases_importer._remove_non_existent_tables_from_db()

        temp_db_cursor.execute(query_tables)
        tables_result = temp_db_cursor.fetchall()
        assert (len(tables_result) == 1 and
            tables_result[0][0] == 'place_classtype_testclasstypetable_to_keep'
        )

def test_import_from_wiki(monkeypatch, temp_db_conn, def_config, special_phrases_importer,
                          placex_table, tokenizer_mock):
    """
        Check that the main import_from_wiki() method is well executed.
        It should create the place_classtype table, the place_id and centroid indexes,
        grand access to the web user and executing the SQL functions for amenities.
        It should also update the database well by deleting or preserving existing entries 
        of the database.
    """
    #Add some data to the database before execution in order to test
    #what is deleted and what is preserved.
    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute("""
            CREATE TABLE place_classtype_amenity_animal_shelter();
            CREATE TABLE place_classtype_wrongclass_wrongtype();""")

    monkeypatch.setattr('nominatim.tools.SpecialPhrasesImporter._get_wiki_content', mock_get_wiki_content)
    tokenizer = tokenizer_mock()
    special_phrases_importer.import_from_wiki(tokenizer, ['en'])

    assert len(tokenizer.analyser_cache['special_phrases']) == 18

    class_test = 'aerialway'
    type_test = 'zip_line'

    assert check_table_exist(temp_db_conn, class_test, type_test)
    assert check_placeid_and_centroid_indexes(temp_db_conn, class_test, type_test)
    assert check_grant_access(temp_db_conn, def_config.DATABASE_WEBUSER, class_test, type_test)
    assert check_table_exist(temp_db_conn, 'amenity', 'animal_shelter')
    assert not check_table_exist(temp_db_conn, 'wrong_class', 'wrong_type')

    #Format (query, should_return_something_bool) use to easily execute all asserts
    queries_tests = set()

    #Used to check that correct place_classtype table already in the datase before is still there.
    query_existing_table = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        AND table_name = 'place_classtype_amenity_animal_shelter';
    """
    queries_tests.add((query_existing_table, True))

    #Used to check that wrong place_classtype table was deleted from the database.
    query_wrong_table = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema='public'
        AND table_name = 'place_classtype_wrongclass_wrongtype';
    """
    queries_tests.add((query_wrong_table, False))

    with temp_db_conn.cursor() as temp_db_cursor:
        for query in queries_tests:
            temp_db_cursor.execute(query[0])
            if (query[1] == True):
                assert temp_db_cursor.fetchone()
            else:
                assert not temp_db_cursor.fetchone()

def mock_get_wiki_content(lang):
    """
        Mock the _get_wiki_content() method to return
        static xml test file content.
    """
    return get_test_xml_wiki_content()

def get_test_xml_wiki_content():
    """
        return the content of the static xml test file.
    """
    xml_test_content_path = (TEST_BASE_DIR / 'testdata' / 'special_phrases_test_content.txt').resolve()
    with open(xml_test_content_path) as xml_content_reader:
        return xml_content_reader.read()

def check_table_exist(temp_db_conn, phrase_class, phrase_type):
    """
        Verify that the place_classtype table exists for the given
        phrase_class and phrase_type.
    """
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute("""
            SELECT *
            FROM information_schema.tables
            WHERE table_type='BASE TABLE'
            AND table_name='{}'""".format(table_name))
        return temp_db_cursor.fetchone()

def check_grant_access(temp_db_conn, user, phrase_class, phrase_type):
    """
        Check that the web user has been granted right access to the
        place_classtype table of the given phrase_class and phrase_type.
    """
    table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)

    with temp_db_conn.cursor() as temp_db_cursor:
        temp_db_cursor.execute("""
                SELECT * FROM information_schema.role_table_grants
                WHERE table_name='{}'
                AND grantee='{}'
                AND privilege_type='SELECT'""".format(table_name, user))
        return temp_db_cursor.fetchone()

def check_placeid_and_centroid_indexes(temp_db_conn, phrase_class, phrase_type):
    """
        Check that the place_id index and centroid index exist for the
        place_classtype table of the given phrase_class and phrase_type.
    """
    index_prefix = 'idx_place_classtype_{}_{}_'.format(phrase_class, phrase_type)

    return (
        temp_db_conn.index_exists(index_prefix + 'centroid')
        and
        temp_db_conn.index_exists(index_prefix + 'place_id')
    )

@pytest.fixture
def special_phrases_importer(temp_db_conn, def_config, temp_phplib_dir_with_migration):
    """
        Return an instance of SpecialPhrasesImporter.
    """
    return SpecialPhrasesImporter(def_config, temp_phplib_dir_with_migration, temp_db_conn)

@pytest.fixture
def temp_phplib_dir_with_migration():
    """
        Return temporary phpdir with migration subdirectory and
        PhraseSettingsToJson.php script inside.
    """
    migration_file = (TEST_BASE_DIR / '..' / 'lib-php' / 'migration'
                      / 'PhraseSettingsToJson.php').resolve()
    with tempfile.TemporaryDirectory() as phpdir:
        (Path(phpdir) / 'migration').mkdir()
        migration_dest_path = (Path(phpdir) / 'migration' / 'PhraseSettingsToJson.php').resolve()
        copyfile(migration_file, migration_dest_path)

        yield Path(phpdir)

@pytest.fixture
def default_phrases(temp_db_cursor):
    temp_db_cursor.execute("""
        CREATE TABLE place_classtype_testclasstypetable_to_delete();
        CREATE TABLE place_classtype_testclasstypetable_to_keep();""")
