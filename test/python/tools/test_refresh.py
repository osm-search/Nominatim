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


@pytest.mark.parametrize("replace", (True, False))
def test_refresh_import_wikipedia(dsn, src_dir, table_factory, temp_db_cursor, replace):
    if replace:
        table_factory('wikipedia_article')
        table_factory('wikipedia_redirect')

    # use the small wikipedia file for the API testdb
    assert refresh.import_wikipedia_articles(dsn, src_dir / 'test' / 'testdb') == 0

    assert temp_db_cursor.table_rows('wikipedia_article') > 0
    assert temp_db_cursor.table_rows('wikipedia_redirect') > 0


def test_recompute_importance(placex_table, table_factory, temp_db_conn, temp_db_cursor):
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION compute_importance(extratags HSTORE,
                                              country_code varchar(2),
                                              osm_type varchar(1), osm_id BIGINT,
                                              OUT importance FLOAT,
                                              OUT wikipedia TEXT)
                               AS $$ SELECT 0.1::float, 'foo'::text $$ LANGUAGE SQL""")

    refresh.recompute_importance(temp_db_conn)
