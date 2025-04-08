import pytest
import tempfile
import json
import os
from unittest.mock import MagicMock

from nominatim_db.errors import UsageError
from nominatim_db.tools.special_phrases.sp_csv_loader import SPCsvLoader
from nominatim_db.tools.special_phrases.special_phrase import SpecialPhrase
from nominatim_db.tools.special_phrases.sp_importer import SPImporter

@pytest.fixture
def sample_style_file():
    sample_data = [
        {
            "keys" : ["emergency"],
            "values" : {
                "fire_hydrant" : "skip",
                "yes" : "skip",
                "no" : "skip",
                "" : "main"
            }
        },
        {
            "keys" : ["historic", "military"],
            "values" : {
                "no" : "skip",
                "yes" : "skip",
                "" : "main"
            }
        },
        {
            "keys" : ["name:prefix", "name:suffix", "name:prefix:*", "name:suffix:*",
                    "name:botanical", "wikidata", "*:wikidata"],
            "values" : {
                "" : "extra"
            }
        },
        {
            "keys" : ["addr:housename"],
            "values" : {
                "" : "name,house"
            }
        },
        {
            "keys": ["highway"],
            "values": {
                "motorway": "main",
                "": "skip"
            }
        }
    ]
    content = ",".join(json.dumps(entry) for entry in sample_data)

    with tempfile.NamedTemporaryFile(mode='w+', delete=False) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    yield tmp_path
    os.remove(tmp_path)


def test_get_sp_style(sample_style_file):
    mock_config = MagicMock()
    mock_config.get_import_style_file.return_value = sample_style_file

    importer = SPImporter(config=mock_config, conn=None, sp_loader=None)
    result = importer.get_sp_style()

    expected = {
        ("highway", "motorway"),
    }

    assert result == expected

@pytest.fixture
def mock_phrase():
    return SpecialPhrase(
        p_label="test",
        p_class="highway",
        p_type="motorway",
        p_operator="eq"
    )

def test_create_classtype_table_and_indexes():
    mock_config = MagicMock()
    mock_config.TABLESPACE_AUX_DATA = ''
    mock_config.DATABASE_WEBUSER = 'www-data'

    mock_cursor = MagicMock()
    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    importer = SPImporter(config=mock_config, conn=mock_conn, sp_loader=None)

    importer._create_place_classtype_table = MagicMock()
    importer._create_place_classtype_indexes = MagicMock()
    importer._grant_access_to_webuser = MagicMock()
    importer.statistics_handler.notify_one_table_created = lambda: print("✓ Created table")
    importer.statistics_handler.notify_one_table_ignored = lambda: print("⨉ Ignored table")

    importer.table_phrases_to_delete = {"place_classtype_highway_motorway"}

    test_pairs = [("highway", "motorway"), ("natural", "peak")]
    importer._create_classtype_table_and_indexes(test_pairs)

    print("create_place_classtype_table calls:")
    for call in importer._create_place_classtype_table.call_args_list:
        print(call)

    print("\ncreate_place_classtype_indexes calls:")
    for call in importer._create_place_classtype_indexes.call_args_list:
        print(call)

    print("\ngrant_access_to_webuser calls:")
    for call in importer._grant_access_to_webuser.call_args_list:
        print(call)

@pytest.fixture
def mock_config():
    config = MagicMock()
    config.TABLESPACE_AUX_DATA = ''
    config.DATABASE_WEBUSER = 'www-data'
    config.load_sub_configuration.return_value = {'blackList': {}, 'whiteList': {}}
    return config


def test_import_phrases_original(mock_config):
    phrase = SpecialPhrase("roundabout", "highway", "motorway", "eq")

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_loader = MagicMock()
    mock_loader.generate_phrases.return_value = [phrase]

    mock_analyzer = MagicMock()
    mock_tokenizer = MagicMock()
    mock_tokenizer.name_analyzer.return_value.__enter__.return_value = mock_analyzer

    importer = SPImporter(config=mock_config, conn=mock_conn, sp_loader=mock_loader)
    importer._fetch_existing_place_classtype_tables = MagicMock()
    importer._create_classtype_table_and_indexes = MagicMock()
    importer._remove_non_existent_tables_from_db = MagicMock()

    importer.import_phrases(tokenizer=mock_tokenizer, should_replace=True)

    assert importer.word_phrases == {("roundabout", "highway", "motorway", "-")}

    mock_analyzer.update_special_phrases.assert_called_once_with(
        importer.word_phrases, True
    )


def test_get_sp_filters_correctly(sample_style_file):
    mock_config = MagicMock()
    mock_config.get_import_style_file.return_value = sample_style_file
    mock_config.load_sub_configuration.return_value = {"blackList": {}, "whiteList": {}}

    importer = SPImporter(config=mock_config, conn=MagicMock(), sp_loader=None)

    allowed_from_db = {("highway", "motorway"), ("historic", "castle")}
    importer.get_sp_db = lambda: allowed_from_db

    result = importer.get_sp()

    expected = {("highway", "motorway")}

    assert result == expected, f"Expected {expected}, got {result}"

def test_get_sp_db_filters_by_count_threshold(mock_config):
    mock_cursor = MagicMock()
    
    # Simulate only results above the threshold being returned (as SQL would)
    # These tuples simulate real SELECT class, type FROM placex GROUP BY ... HAVING COUNT(*) > 100
    mock_cursor.fetchall.return_value = [
        ("highway", "motorway"),
        ("historic", "castle")
    ]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    importer = SPImporter(config=mock_config, conn=mock_conn, sp_loader=None)

    result = importer.get_sp_db()

    expected = {
        ("highway", "motorway"),
        ("historic", "castle")
    }

    assert result == expected
    mock_cursor.execute.assert_called_once()
