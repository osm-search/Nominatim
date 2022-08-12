# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for functions to maintain the artificial postcode table.
"""
import subprocess

import pytest

from nominatim.tools import postcodes
from nominatim.data import country_info
import dummy_tokenizer

class MockPostcodeTable:
    """ A location_postcode table for testing.
    """
    def __init__(self, conn):
        self.conn = conn
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE location_postcode (
                               place_id BIGINT,
                               parent_place_id BIGINT,
                               rank_search SMALLINT,
                               rank_address SMALLINT,
                               indexed_status SMALLINT,
                               indexed_date TIMESTAMP,
                               country_code varchar(2),
                               postcode TEXT,
                               geometry GEOMETRY(Geometry, 4326))""")
            cur.execute("""CREATE OR REPLACE FUNCTION token_normalized_postcode(postcode TEXT)
                           RETURNS TEXT AS $$ BEGIN RETURN postcode; END; $$ LANGUAGE plpgsql;

                           CREATE OR REPLACE FUNCTION get_country_code(place geometry)
                           RETURNS TEXT AS $$ BEGIN 
                           RETURN null;
                           END; $$ LANGUAGE plpgsql;
                        """)
        conn.commit()

    def add(self, country, postcode, x, y):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO location_postcode (place_id, indexed_status,
                                                          country_code, postcode,
                                                          geometry)
                           VALUES (nextval('seq_place'), 1, %s, %s,
                                   'SRID=4326;POINT(%s %s)')""",
                        (country, postcode, x, y))
        self.conn.commit()


    @property
    def row_set(self):
        with self.conn.cursor() as cur:
            cur.execute("""SELECT country_code, postcode,
                                  ST_X(geometry), ST_Y(geometry)
                           FROM location_postcode""")
            return set((tuple(row) for row in cur))


@pytest.fixture
def tokenizer():
    return dummy_tokenizer.DummyTokenizer(None, None)


@pytest.fixture
def postcode_table(def_config, temp_db_conn, placex_table):
    country_info.setup_country_config(def_config)
    return MockPostcodeTable(temp_db_conn)


@pytest.fixture
def insert_implicit_postcode(placex_table, place_row):
    """
        Inserts data into the placex and place table
        which can then be used to compute one postcode.
    """
    def _insert_implicit_postcode(osm_id, country, geometry, address):
        placex_table.add(osm_id=osm_id, country=country, geom=geometry)
        place_row(osm_id=osm_id, geom='SRID=4326;'+geometry, address=address)

    return _insert_implicit_postcode


def test_postcodes_empty(dsn, postcode_table, place_table,
                         tmp_path, tokenizer):
    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert not postcode_table.row_set


def test_postcodes_add_new(dsn, postcode_table, tmp_path,
                           insert_implicit_postcode, tokenizer):
    insert_implicit_postcode(1, 'xx', 'POINT(10 12)', dict(postcode='9486'))
    postcode_table.add('yy', '9486', 99, 34)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', '9486', 10, 12), }


def test_postcodes_replace_coordinates(dsn, postcode_table, tmp_path,
                                       insert_implicit_postcode, tokenizer):
    insert_implicit_postcode(1, 'xx', 'POINT(10 12)', dict(postcode='AB 4511'))
    postcode_table.add('xx', 'AB 4511', 99, 34)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12)}


def test_postcodes_replace_coordinates_close(dsn, postcode_table, tmp_path,
                                             insert_implicit_postcode, tokenizer):
    insert_implicit_postcode(1, 'xx', 'POINT(10 12)', dict(postcode='AB 4511'))
    postcode_table.add('xx', 'AB 4511', 10, 11.99999)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 11.99999)}


def test_postcodes_remove(dsn, postcode_table, tmp_path,
                          insert_implicit_postcode, tokenizer):
    insert_implicit_postcode(1, 'xx', 'POINT(10 12)', dict(postcode='AB 4511'))
    postcode_table.add('xx', 'badname', 10, 12)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12)}


def test_postcodes_ignore_empty_country(dsn, postcode_table, tmp_path,
                                        insert_implicit_postcode, tokenizer):
    insert_implicit_postcode(1, None, 'POINT(10 12)', dict(postcode='AB 4511'))
    postcodes.update_postcodes(dsn, tmp_path, tokenizer)
    assert not postcode_table.row_set


def test_postcodes_remove_all(dsn, postcode_table, place_table,
                              tmp_path, tokenizer):
    postcode_table.add('ch', '5613', 10, 12)
    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert not postcode_table.row_set


def test_postcodes_multi_country(dsn, postcode_table, tmp_path,
                                 insert_implicit_postcode, tokenizer):
    insert_implicit_postcode(1, 'de', 'POINT(10 12)', dict(postcode='54451'))
    insert_implicit_postcode(2, 'cc', 'POINT(100 56)', dict(postcode='DD23 T'))
    insert_implicit_postcode(3, 'de', 'POINT(10.3 11.0)', dict(postcode='54452'))
    insert_implicit_postcode(4, 'cc', 'POINT(10.3 11.0)', dict(postcode='54452'))

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('de', '54451', 10, 12),
                                      ('de', '54452', 10.3, 11.0),
                                      ('cc', '54452', 10.3, 11.0),
                                      ('cc', 'DD23 T', 100, 56)}


@pytest.mark.parametrize("gzipped", [True, False])
def test_postcodes_extern(dsn, postcode_table, tmp_path,
                          insert_implicit_postcode, tokenizer, gzipped):
    insert_implicit_postcode(1, 'xx', 'POINT(10 12)', dict(postcode='AB 4511'))

    extfile = tmp_path / 'xx_postcodes.csv'
    extfile.write_text("postcode,lat,lon\nAB 4511,-4,-1\nCD 4511,-5, -10")

    if gzipped:
        subprocess.run(['gzip', str(extfile)])
        assert not extfile.is_file()

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12),
                                      ('xx', 'CD 4511', -10, -5)}


def test_postcodes_extern_bad_column(dsn, postcode_table, tmp_path, 
                                     insert_implicit_postcode, tokenizer):
    insert_implicit_postcode(1, 'xx', 'POINT(10 12)', dict(postcode='AB 4511'))

    extfile = tmp_path / 'xx_postcodes.csv'
    extfile.write_text("postode,lat,lon\nAB 4511,-4,-1\nCD 4511,-5, -10")

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12)}


def test_postcodes_extern_bad_number(dsn, insert_implicit_postcode,
                                     postcode_table, tmp_path, tokenizer):
    insert_implicit_postcode(1, 'xx', 'POINT(10 12)', dict(postcode='AB 4511'))

    extfile = tmp_path / 'xx_postcodes.csv'
    extfile.write_text("postcode,lat,lon\nXX 4511,-4,NaN\nCD 4511,-5, -10\n34,200,0")

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12),
                                      ('xx', 'CD 4511', -10, -5)}

def test_can_compute(dsn, table_factory):
    assert not postcodes.can_compute(dsn)
    table_factory('place')
    assert postcodes.can_compute(dsn)


def test_no_placex_entry(dsn, tmp_path, temp_db_cursor, place_row, postcode_table, tokenizer):
    #Rewrite the get_country_code function to verify its execution.
    temp_db_cursor.execute("""
        CREATE OR REPLACE FUNCTION get_country_code(place geometry)
        RETURNS TEXT AS $$ BEGIN 
        RETURN 'yy';
        END; $$ LANGUAGE plpgsql;
    """)
    place_row(geom='SRID=4326;POINT(10 12)', address=dict(postcode='AB 4511'))
    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('yy', 'AB 4511', 10, 12)}


def test_discard_badly_formatted_postcodes(dsn, tmp_path, temp_db_cursor, place_row, postcode_table, tokenizer):
    #Rewrite the get_country_code function to verify its execution.
    temp_db_cursor.execute("""
        CREATE OR REPLACE FUNCTION get_country_code(place geometry)
        RETURNS TEXT AS $$ BEGIN 
        RETURN 'fr';
        END; $$ LANGUAGE plpgsql;
    """)
    place_row(geom='SRID=4326;POINT(10 12)', address=dict(postcode='AB 4511'))
    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert not postcode_table.row_set
