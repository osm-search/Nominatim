"""
Tests for function for importing address ranks.
"""
import json
from pathlib import Path

import pytest

from nominatim.tools.refresh import load_address_levels, load_address_levels_from_file

def test_load_ranks_def_config(temp_db_conn, temp_db_cursor, def_config):
    load_address_levels_from_file(temp_db_conn, Path(def_config.ADDRESS_LEVEL_CONFIG))

    assert temp_db_cursor.table_rows('address_levels') > 0

def test_load_ranks_from_file(temp_db_conn, temp_db_cursor, tmp_path):
    test_file = tmp_path / 'test_levels.json'
    test_file.write_text('[{"tags":{"place":{"sea":2}}}]')

    load_address_levels_from_file(temp_db_conn, test_file)

    assert temp_db_cursor.table_rows('address_levels') > 0


def test_load_ranks_from_broken_file(temp_db_conn, tmp_path):
    test_file = tmp_path / 'test_levels.json'
    test_file.write_text('[{"tags":"place":{"sea":2}}}]')

    with pytest.raises(json.decoder.JSONDecodeError):
        load_address_levels_from_file(temp_db_conn, test_file)


def test_load_ranks_country(temp_db_conn, temp_db_cursor):
    load_address_levels(temp_db_conn, 'levels',
                        [{"tags": {"place": {"village": 14}}},
                         {"countries": ['de'],
                          "tags": {"place": {"village": 15}}},
                         {"countries": ['uk', 'us'],
                          "tags": {"place": {"village": 16}}}
                        ])

    assert temp_db_cursor.row_set('SELECT * FROM levels') == \
           set([(None, 'place', 'village', 14, 14),
                ('de', 'place', 'village', 15, 15),
                ('uk', 'place', 'village', 16, 16),
                ('us', 'place', 'village', 16, 16),
               ])


def test_load_ranks_default_value(temp_db_conn, temp_db_cursor):
    load_address_levels(temp_db_conn, 'levels',
                        [{"tags": {"boundary": {"": 28}}},
                         {"countries": ['hu'],
                          "tags": {"boundary": {"": 29}}}
                        ])

    assert temp_db_cursor.row_set('SELECT * FROM levels') == \
           set([(None, 'boundary', None, 28, 28),
                ('hu', 'boundary', None, 29, 29),
               ])


def test_load_ranks_multiple_keys(temp_db_conn, temp_db_cursor):
    load_address_levels(temp_db_conn, 'levels',
                        [{"tags": {"place": {"city": 14},
                                   "boundary": {"administrative2" : 4}}
                         }])

    assert temp_db_cursor.row_set('SELECT * FROM levels') == \
           set([(None, 'place', 'city', 14, 14),
                (None, 'boundary', 'administrative2', 4, 4),
               ])


def test_load_ranks_address(temp_db_conn, temp_db_cursor):
    load_address_levels(temp_db_conn, 'levels',
                        [{"tags": {"place": {"city": 14,
                                             "town" : [14, 13]}}
                         }])

    assert temp_db_cursor.row_set('SELECT * FROM levels') == \
           set([(None, 'place', 'city', 14, 14),
                (None, 'place', 'town', 14, 13),
               ])
