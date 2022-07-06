# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for various refresh functions.
"""
from pathlib import Path

import pytest

from nominatim.tools import refresh

def test_refresh_import_wikipedia_not_existing(dsn):
    assert refresh.import_wikipedia_articles(dsn, Path('.')) == 1


def test_refresh_import_osm_views_geotiff_not_existing(dsn):
    assert refresh.import_osm_views_geotiff(dsn, Path('.')) == 1


@pytest.mark.parametrize("replace", (True, False))
def test_refresh_import_wikipedia(dsn, src_dir, table_factory, temp_db_cursor, replace):
    if replace:
        table_factory('wikipedia_article')
        table_factory('wikipedia_redirect')

    # use the small wikipedia file for the API testdb
    assert refresh.import_wikipedia_articles(dsn, src_dir / 'test' / 'testdb') == 0

    assert temp_db_cursor.table_rows('wikipedia_article') > 0
    assert temp_db_cursor.table_rows('wikipedia_redirect') > 0


@pytest.mark.parametrize("replace", (True, False))
def test_refresh_import_osm_views_geotiff(dsn, src_dir, table_factory, temp_db_cursor, replace):
    if replace:
        table_factory('osmviews')

    # use the small osm views GeoTIFF file for the API testdb
    assert refresh.import_osm_views_geotiff(dsn, src_dir / 'test' / 'testdb') == 0

    assert temp_db_cursor.table_rows('osmviews') > 0


def test_recompute_importance(placex_table, table_factory, temp_db_conn, temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION compute_importance(extratags HSTORE,
                                              country_code varchar(2),
                                              osm_type varchar(1), osm_id BIGINT,
                                              OUT importance FLOAT,
                                              OUT wikipedia TEXT)
                               AS $$ SELECT 0.1::float, 'foo'::text $$ LANGUAGE SQL""")

    refresh.recompute_importance(temp_db_conn)


@pytest.mark.parametrize('osm_type', ('N', 'W', 'R'))
def test_invalidate_osm_object_simple(placex_table, osm_type, temp_db_conn, temp_db_cursor):
    placex_table.add(osm_type=osm_type, osm_id=57283)

    refresh.invalidate_osm_object(osm_type, 57283, temp_db_conn, recursive=False)
    temp_db_conn.commit()

    assert 2 == temp_db_cursor.scalar("""SELECT indexed_status FROM placex
                                         WHERE osm_type = %s and osm_id = %s""",
                                      (osm_type, 57283))


def test_invalidate_osm_object_nonexisting_simple(placex_table, temp_db_conn, temp_db_cursor):
    placex_table.add(osm_type='W', osm_id=57283)

    refresh.invalidate_osm_object('N', 57283, temp_db_conn, recursive=False)
    temp_db_conn.commit()

    assert 0 == temp_db_cursor.scalar("""SELECT count(*) FROM placex
                                         WHERE indexed_status > 0""")


@pytest.mark.parametrize('osm_type', ('N', 'W', 'R'))
def test_invalidate_osm_object_recursive(placex_table, osm_type, temp_db_conn, temp_db_cursor):
    placex_table.add(osm_type=osm_type, osm_id=57283)

    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION place_force_update(placeid BIGINT)
                              RETURNS BOOLEAN AS $$
                              BEGIN
                                UPDATE placex SET indexed_status = 522
                                WHERE place_id = placeid;
                                RETURN TRUE;
                              END;
                              $$
                              LANGUAGE plpgsql;""")

    refresh.invalidate_osm_object(osm_type, 57283, temp_db_conn)
    temp_db_conn.commit()

    assert 522 == temp_db_cursor.scalar("""SELECT indexed_status FROM placex
                                           WHERE osm_type = %s and osm_id = %s""",
                                        (osm_type, 57283))
