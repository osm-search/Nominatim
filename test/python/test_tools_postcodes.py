"""
Tests for functions to maintain the artificial postcode table.
"""
import subprocess

import pytest

from nominatim.tools import postcodes
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
def postcode_table(temp_db_conn, placex_table, word_table):
    return MockPostcodeTable(temp_db_conn)


def test_import_postcodes_empty(dsn, postcode_table, tmp_path, tokenizer):
    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert not postcode_table.row_set


def test_import_postcodes_add_new(dsn, placex_table, postcode_table, tmp_path, tokenizer):
    placex_table.add(country='xx', geom='POINT(10 12)',
                     address=dict(postcode='9486'))
    postcode_table.add('yy', '9486', 99, 34)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', '9486', 10, 12),
                                      ('yy', '9486', 99, 34)}


def test_import_postcodes_replace_coordinates(dsn, placex_table, postcode_table, tmp_path, tokenizer):
    placex_table.add(country='xx', geom='POINT(10 12)',
                     address=dict(postcode='AB 4511'))
    postcode_table.add('xx', 'AB 4511', 99, 34)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12)}


def test_import_postcodes_replace_coordinates_close(dsn, placex_table, postcode_table, tmp_path, tokenizer):
    placex_table.add(country='xx', geom='POINT(10 12)',
                     address=dict(postcode='AB 4511'))
    postcode_table.add('xx', 'AB 4511', 10, 11.99999)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 11.99999)}


def test_import_postcodes_remove(dsn, placex_table, postcode_table, tmp_path, tokenizer):
    placex_table.add(country='xx', geom='POINT(10 12)',
                     address=dict(postcode='AB 4511'))
    postcode_table.add('xx', 'badname', 10, 12)

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12)}


def test_import_postcodes_multi_country(dsn, placex_table, postcode_table, tmp_path, tokenizer):
    placex_table.add(country='de', geom='POINT(10 12)',
                     address=dict(postcode='54451'))
    placex_table.add(country='cc', geom='POINT(100 56)',
                     address=dict(postcode='DD23 T'))
    placex_table.add(country='de', geom='POINT(10.3 11.0)',
                     address=dict(postcode='54452'))
    placex_table.add(country='cc', geom='POINT(10.3 11.0)',
                     address=dict(postcode='54452'))

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('de', '54451', 10, 12),
                                      ('de', '54452', 10.3, 11.0),
                                      ('cc', '54452', 10.3, 11.0),
                                      ('cc', 'DD23 T', 100, 56)}


@pytest.mark.parametrize("gzipped", [True, False])
def test_import_postcodes_extern(dsn, placex_table, postcode_table, tmp_path,
                                 tokenizer, gzipped):
    placex_table.add(country='xx', geom='POINT(10 12)',
                     address=dict(postcode='AB 4511'))

    extfile = tmp_path / 'xx_postcodes.csv'
    extfile.write_text("postcode,lat,lon\nAB 4511,-4,-1\nCD 4511,-5, -10")

    if gzipped:
        subprocess.run(['gzip', str(extfile)])
        assert not extfile.is_file()

    postcodes.update_postcodes(dsn, tmp_path, tokenizer)

    assert postcode_table.row_set == {('xx', 'AB 4511', 10, 12),
                                      ('xx', 'CD 4511', -10, -5)}

