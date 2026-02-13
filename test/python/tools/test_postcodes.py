# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for functions to maintain the artificial postcode table.
"""
import subprocess

import pytest

from psycopg.rows import tuple_row

from nominatim_db.tools import postcodes
from nominatim_db.data import country_info

import dummy_tokenizer


@pytest.fixture
def insert_implicit_postcode(placex_row, place_postcode_row):
    """ Insert data into the placex and place table
        which can then be used to compute one postcode.
    """
    def _insert_implicit_postcode(osm_id, country, geometry, postcode, in_placex=False):
        if in_placex:
            placex_row(osm_id=osm_id, country=country, geom=geometry,
                       centroid=geometry,
                       address={'postcode': postcode})
        else:
            place_postcode_row(osm_id=osm_id, centroid=geometry,
                               country=country, postcode=postcode)
    return _insert_implicit_postcode


@pytest.fixture
def insert_postcode_area(place_postcode_row):
    """ Insert an area around a centroid to the postcode table.
    """
    def _do(osm_id, country, postcode, x, y):
        x1, x2, y1, y2 = x - 0.001, x + 0.001, y - 0.001, y + 0.001
        place_postcode_row(osm_type='R', osm_id=osm_id, postcode=postcode, country=country,
                           centroid=f"POINT({x} {y})",
                           geom=f"POLYGON(({x1} {y1}, {x1} {y2}, {x2} {y2}, {x2} {y1}, {x1} {y1}))")
    return _do


@pytest.fixture
def postcode_update(dsn, temp_db_conn):
    tokenizer = dummy_tokenizer.DummyTokenizer(None)

    def _do(data_path=None):
        with temp_db_conn.cursor() as cur:
            cur.execute("""CREATE TRIGGER location_postcodes_before_update
                            BEFORE UPDATE ON location_postcodes
                            FOR EACH ROW EXECUTE PROCEDURE postcodes_update()""")
            cur.execute("""CREATE TRIGGER location_postcodes_before_delete
                            BEFORE DELETE ON location_postcodes
                            FOR EACH ROW EXECUTE PROCEDURE postcodes_delete()""")
            cur.execute("""CREATE TRIGGER location_postcodes_before_insert
                            BEFORE INSERT ON location_postcodes
                            FOR EACH ROW EXECUTE PROCEDURE postcodes_insert()""")
        temp_db_conn.commit()
        postcodes.update_postcodes(dsn, data_path, tokenizer)
    return _do


class TestPostcodes:
    @pytest.fixture(autouse=True)
    def setup(self, def_config, postcode_table, placex_table, place_postcode_table,
              load_sql, temp_db_conn):
        self.conn = temp_db_conn
        country_info.setup_country_config(def_config)
        load_sql('functions/postcode_triggers.sql')

        temp_db_conn.execute("""
            CREATE OR REPLACE FUNCTION token_normalized_postcode(postcode TEXT)
            RETURNS TEXT AS $$
              SELECT postcode
            $$ LANGUAGE sql;

            CREATE OR REPLACE FUNCTION get_country_code(place geometry)
            RETURNS TEXT AS $$
              SELECT NULL
            $$ LANGUAGE sql;

            CREATE OR REPLACE FUNCTION expand_by_meters(geom GEOMETRY, meters FLOAT)
            RETURNS GEOMETRY AS $$
              SELECT ST_Envelope(ST_Buffer(geom::geography, meters, 1)::geometry)
            $$ LANGUAGE sql;
        """)

    @property
    def row_set(self):
        with self.conn.cursor(row_factory=tuple_row) as cur:
            cur.execute("""SELECT osm_id, country_code, postcode,
                                  ST_X(centroid), ST_Y(centroid)
                           FROM location_postcodes""")
            return {r for r in cur}

    def test_postcodes_empty(self, postcode_update):
        postcode_update()

        assert not self.row_set

    @pytest.mark.parametrize('in_placex', [True, False])
    def test_postcodes_add_new_point(self, postcode_update, postcode_row,
                                     insert_implicit_postcode, in_placex):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', '9486', in_placex)
        postcode_row('yy', '9486', 99, 34)

        postcode_update()

        assert self.row_set == {(None, 'xx', '9486', 10, 12), }

    def test_postcodes_add_new_area(self, postcode_update, insert_postcode_area):
        insert_postcode_area(345, 'de', '10445', 23.5, 46.2)

        postcode_update()

        assert self.row_set == {(345, 'de', '10445', 23.5, 46.2)}

    @pytest.mark.parametrize('in_placex', [True, False])
    def test_postcodes_add_area_and_point(self, postcode_update, insert_postcode_area,
                                          insert_implicit_postcode, in_placex):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', '10445', in_placex)
        insert_postcode_area(345, 'xx', '10445', 23.5, 46.2)

        postcode_update()

        assert self.row_set == {(345, 'xx', '10445', 23.5, 46.2)}

    @pytest.mark.parametrize('in_placex', [True, False])
    def test_postcodes_add_point_within_area(self, postcode_update, insert_postcode_area,
                                             insert_implicit_postcode, in_placex):
        insert_implicit_postcode(1, 'xx', 'POINT(23.5 46.2)', '10446', in_placex)
        insert_postcode_area(345, 'xx', '10445', 23.5, 46.2)

        postcode_update()

        assert self.row_set == {(345, 'xx', '10445', 23.5, 46.2)}

    @pytest.mark.parametrize('coords', [(99, 34), (10, 34), (99, 12),
                                        (9, 34), (9, 11), (23, 11)])
    def test_postcodes_replace_coordinates(self, postcode_update, postcode_row, tmp_path,
                                           insert_implicit_postcode, coords):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', 'AB 4511')
        postcode_row('xx', 'AB 4511', *coords)

        postcode_update(tmp_path)

        assert self.row_set == {(None, 'xx', 'AB 4511', 10, 12)}

    def test_postcodes_replace_coordinates_close(self, postcode_update, postcode_row,
                                                 insert_implicit_postcode):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', 'AB 4511')
        postcode_row('xx', 'AB 4511', 10, 11.99999999)

        postcode_update()

        assert self.row_set == {(None, 'xx', 'AB 4511', 10, 11.99999999)}

    def test_postcodes_remove_point(self, postcode_update, postcode_row,
                                    insert_implicit_postcode):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', 'AB 4511')
        postcode_row('xx', 'badname', 10, 12)

        postcode_update()

        assert self.row_set == {(None, 'xx', 'AB 4511', 10, 12)}

    def test_postcodes_ignore_empty_country(self, postcode_update, insert_implicit_postcode):
        insert_implicit_postcode(1, None, 'POINT(10 12)', 'AB 4511')
        postcode_update()
        assert not self.row_set

    def test_postcodes_remove_all(self, postcode_update, postcode_row, place_postcode_table):
        postcode_row('ch', '5613', 10, 12)
        postcode_update()

        assert not self.row_set

    def test_postcodes_multi_country(self, postcode_update,
                                     insert_implicit_postcode):
        insert_implicit_postcode(1, 'de', 'POINT(10 12)', '54451')
        insert_implicit_postcode(2, 'cc', 'POINT(100 56)', 'DD23 T')
        insert_implicit_postcode(3, 'de', 'POINT(10.3 11.0)', '54452')
        insert_implicit_postcode(4, 'cc', 'POINT(10.3 11.0)', '54452')

        postcode_update()

        assert self.row_set == {(None, 'de', '54451', 10, 12),
                                (None, 'de', '54452', 10.3, 11.0),
                                (None, 'cc', '54452', 10.3, 11.0),
                                (None, 'cc', 'DD23 T', 100, 56)}

    @pytest.mark.parametrize("gzipped", [True, False])
    def test_postcodes_extern(self, postcode_update, tmp_path,
                              insert_implicit_postcode, gzipped):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', 'AB 4511')

        extfile = tmp_path / 'xx_postcodes.csv'
        extfile.write_text("postcode,lat,lon\nAB 4511,-4,-1\nCD 4511,-5, -10", encoding='utf-8')

        if gzipped:
            subprocess.run(['gzip', str(extfile)])
            assert not extfile.is_file()

        postcode_update(tmp_path)

        assert self.row_set == {(None, 'xx', 'AB 4511', 10, 12),
                                (None, 'xx', 'CD 4511', -10, -5)}

    def test_postcodes_extern_bad_column(self, postcode_update, tmp_path,
                                         insert_implicit_postcode):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', 'AB 4511')

        extfile = tmp_path / 'xx_postcodes.csv'
        extfile.write_text("postode,lat,lon\nAB 4511,-4,-1\nCD 4511,-5, -10", encoding='utf-8')

        postcode_update(tmp_path)

        assert self.row_set == {(None, 'xx', 'AB 4511', 10, 12)}

    def test_postcodes_extern_bad_number(self, postcode_update, insert_implicit_postcode,
                                         tmp_path):
        insert_implicit_postcode(1, 'xx', 'POINT(10 12)', 'AB 4511')

        extfile = tmp_path / 'xx_postcodes.csv'
        extfile.write_text(
            "postcode,lat,lon\nXX 4511,-4,NaN\nCD 4511,-5, -10\n34,200,0", encoding='utf-8')

        postcode_update(tmp_path)

        assert self.row_set == {(None, 'xx', 'AB 4511', 10, 12),
                                (None, 'xx', 'CD 4511', -10, -5)}

    def test_no_placex_entry(self, postcode_update, temp_db_cursor, place_postcode_row):
        # Rewrite the get_country_code function to verify its execution.
        temp_db_cursor.execute("""
            CREATE OR REPLACE FUNCTION get_country_code(place geometry) RETURNS TEXT AS $$
              SELECT 'yy' $$ LANGUAGE sql""")
        place_postcode_row(centroid='POINT(10 12)', postcode='AB 4511')
        postcode_update()

        assert self.row_set == {(None, 'yy', 'AB 4511', 10, 12)}

    def test_discard_badly_formatted_postcodes(self, postcode_update, place_postcode_row):
        place_postcode_row(centroid='POINT(10 12)', country='fr', postcode='AB 4511')
        postcode_update()

        assert not self.row_set


def test_can_compute(dsn, table_factory):
    assert not postcodes.can_compute(dsn)
    table_factory('place_postcode')
    assert postcodes.can_compute(dsn)
