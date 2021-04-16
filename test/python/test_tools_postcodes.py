"""
Tests for functions to maintain the artificial postcode table.
"""

import pytest

from nominatim.tools import postcodes

@pytest.fixture
def postcode_table(temp_db_with_extensions, temp_db_cursor, table_factory,
                   placex_table, word_table):
    table_factory('location_postcode',
                  """ place_id BIGINT,
                      parent_place_id BIGINT,
                      rank_search SMALLINT,
                      rank_address SMALLINT,
                      indexed_status SMALLINT,
                      indexed_date TIMESTAMP,
                      country_code varchar(2),
                      postcode TEXT,
                      geometry GEOMETRY(Geometry, 4326)""")
    temp_db_cursor.execute('CREATE SEQUENCE seq_place')
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_postcode_id(postcode TEXT)
                              RETURNS INTEGER AS $$ BEGIN RETURN 1; END; $$ LANGUAGE plpgsql;
                           """)


def test_import_postcodes_empty(dsn, temp_db_cursor, postcode_table, tmp_path):
    postcodes.import_postcodes(dsn, tmp_path)

    assert temp_db_cursor.table_exists('gb_postcode')
    assert temp_db_cursor.table_exists('us_postcode')
    assert temp_db_cursor.table_rows('location_postcode') == 0


def test_import_postcodes_from_placex(dsn, temp_db_cursor, postcode_table, tmp_path):
    temp_db_cursor.execute("""
        INSERT INTO placex (place_id, country_code, address, geometry)
          VALUES (1, 'xx', '"postcode"=>"9486"', 'SRID=4326;POINT(10 12)')
    """)

    postcodes.import_postcodes(dsn, tmp_path)

    rows = temp_db_cursor.row_set(""" SELECT postcode, country_code,
                                      ST_X(geometry), ST_Y(geometry)
                                      FROM location_postcode""")
    print(rows)
    assert len(rows) == 1
    assert rows == set((('9486', 'xx', 10, 12), ))

