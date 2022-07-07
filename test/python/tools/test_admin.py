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
from nominatim.tokenizer import factory

@pytest.fixture(autouse=True)
def create_placex_table(project_env, tokenizer_mock, temp_db_cursor, placex_table):
    """ All tests in this module require the placex table to be set up.
    """
    temp_db_cursor.execute("DROP TYPE IF EXISTS prepare_update_info CASCADE")
    temp_db_cursor.execute("""CREATE TYPE prepare_update_info AS (
                             name HSTORE,
                             address HSTORE,
                             rank_address SMALLINT,
                             country_code TEXT,
                             class TEXT,
                             type TEXT,
                             linked_place_id BIGINT
                           )""")
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION placex_indexing_prepare(p placex,
                                                     OUT result prepare_update_info)
                           AS $$
                           BEGIN
                             result.address := p.address;
                             result.name := p.name;
                             result.class := p.class;
                             result.type := p.type;
                             result.country_code := p.country_code;
                             result.rank_address := p.rank_address;
                           END;
                           $$ LANGUAGE plpgsql STABLE;
                        """)
    factory.create_tokenizer(project_env)


def test_analyse_indexing_no_objects(project_env):
    with pytest.raises(UsageError):
        admin.analyse_indexing(project_env)


@pytest.mark.parametrize("oid", ['1234', 'N123a', 'X123'])
def test_analyse_indexing_bad_osmid(project_env, oid):
    with pytest.raises(UsageError):
        admin.analyse_indexing(project_env, osm_id=oid)


def test_analyse_indexing_unknown_osmid(project_env):
    with pytest.raises(UsageError):
        admin.analyse_indexing(project_env, osm_id='W12345674')


def test_analyse_indexing_with_place_id(project_env, temp_db_cursor):
    temp_db_cursor.execute("INSERT INTO placex (place_id) VALUES(12345)")

    admin.analyse_indexing(project_env, place_id=12345)


def test_analyse_indexing_with_osm_id(project_env, temp_db_cursor):
    temp_db_cursor.execute("""INSERT INTO placex (place_id, osm_type, osm_id)
                              VALUES(9988, 'N', 10000)""")

    admin.analyse_indexing(project_env, osm_id='N10000')
