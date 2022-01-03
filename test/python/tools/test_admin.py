# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for maintenance and analysis functions.
"""
import pytest

from nominatim.errors import UsageError
from nominatim.tools import admin

@pytest.fixture(autouse=True)
def create_placex_table(placex_table):
    """ All tests in this module require the placex table to be set up.
    """


def test_analyse_indexing_no_objects(temp_db_conn):
    with pytest.raises(UsageError):
        admin.analyse_indexing(temp_db_conn)


@pytest.mark.parametrize("oid", ['1234', 'N123a', 'X123'])
def test_analyse_indexing_bad_osmid(temp_db_conn, oid):
    with pytest.raises(UsageError):
        admin.analyse_indexing(temp_db_conn, osm_id=oid)


def test_analyse_indexing_unknown_osmid(temp_db_conn):
    with pytest.raises(UsageError):
        admin.analyse_indexing(temp_db_conn, osm_id='W12345674')


def test_analyse_indexing_with_place_id(temp_db_conn, temp_db_cursor):
    temp_db_cursor.execute("INSERT INTO placex (place_id) VALUES(12345)")

    admin.analyse_indexing(temp_db_conn, place_id=12345)


def test_analyse_indexing_with_osm_id(temp_db_conn, temp_db_cursor):
    temp_db_cursor.execute("""INSERT INTO placex (place_id, osm_type, osm_id)
                              VALUES(9988, 'N', 10000)""")

    admin.analyse_indexing(temp_db_conn, osm_id='N10000')
