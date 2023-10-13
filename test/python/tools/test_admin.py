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


class TestAdminCleanDeleted:

    @pytest.fixture(autouse=True)
    def setup_polygon_delete(self, project_env, table_factory, temp_db_cursor):
        """ Set up import_polygon_delete table and simplified place_force_delete function
        """
        self.project_env = project_env
        self.temp_db_cursor = temp_db_cursor
        table_factory('import_polygon_delete',
                      """osm_id BIGINT,
                      osm_type CHAR(1),
                      class TEXT NOT NULL,
                      type TEXT NOT NULL""",
                      ((100, 'N', 'boundary', 'administrative'),
                      (145, 'N', 'boundary', 'administrative'),
                      (175, 'R', 'landcover', 'grass')))
        table_factory('place_to_be_deleted',
                      """osm_id BIGINT,
                      osm_type CHAR(1),
                      class TEXT NOT NULL,
                      type TEXT NOT NULL,
                      deferred BOOLEAN""")
        temp_db_cursor.execute("""INSERT INTO placex (place_id, osm_id, osm_type, class, type, indexed_date, indexed_status)
                              VALUES(1, 100, 'N', 'boundary', 'administrative', current_date - INTERVAL '1 month', 1),
                               (2, 145, 'N', 'boundary', 'administrative', current_date - INTERVAL '1 month', 1),
                               (3, 175, 'R', 'landcover', 'grass', current_date - INTERVAL '1 month', 1)""")
        temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION flush_deleted_places()
                               RETURNS INTEGER
                               AS $$
                               BEGIN
                                UPDATE placex p SET indexed_status = 100 FROM place_to_be_deleted d
                                WHERE p.osm_type = d.osm_type
                                AND p.osm_id = d.osm_id
                                AND p.class = d.class
                                AND p.type = d.type
                                AND NOT deferred;
                               TRUNCATE TABLE place_to_be_deleted;
                                RETURN NULL;
                               END;
                               $$
                               LANGUAGE plpgsql;
                               """)
        temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION place_force_delete(placeid BIGINT)
                               RETURNS BOOLEAN
                               AS $$
                               DECLARE 
                                osmid BIGINT;
                                osmtype character(1);
                                pclass text;
                                ptype text;
                               BEGIN
                                SELECT osm_type, osm_id, class, type FROM placex WHERE place_id = placeid INTO osmtype, osmid, pclass, ptype;
                                DELETE FROM import_polygon_delete WHERE osm_type = osmtype AND osm_id = osmid AND class = pclass AND type = ptype;
                                INSERT INTO place_to_be_deleted (osm_type, osm_id, class, type, deferred)
                                        VALUES(osmtype, osmid, pclass, ptype, false);
                                PERFORM flush_deleted_places();
                                RETURN TRUE;
                               END;
                               $$
                               LANGUAGE plpgsql;
                               """)
        

    def test_admin_clean_deleted_no_records(self):
        admin.clean_deleted_relations(self.project_env, age='1 year')
        assert self.temp_db_cursor.row_set('SELECT osm_id, osm_type, class, type, indexed_status FROM placex') == {(100, 'N', 'boundary', 'administrative', 1),
                                                                                                                   (145, 'N', 'boundary', 'administrative', 1),
                                                                                                                   (175, 'R', 'landcover', 'grass', 1)}
        assert self.temp_db_cursor.table_rows('import_polygon_delete') == 3


    def test_admin_clean_deleted_no_age(self):
        with pytest.raises(UsageError):
            admin.clean_deleted_relations(self.project_env)


    @pytest.mark.parametrize('test_age', ['T week', '1 welk', 'P1E'])
    def test_admin_clean_deleted_bad_age(self, test_age):
        with pytest.raises(UsageError):
            admin.clean_deleted_relations(self.project_env, age = test_age)


    @pytest.mark.parametrize('test_age', ['1 week', 'P3D', '5 hours'])
    def test_admin_clean_deleted(self, test_age):
        admin.clean_deleted_relations(self.project_env, age = test_age)
        assert self.temp_db_cursor.row_set('SELECT osm_id, osm_type, class, type, indexed_status FROM placex') == {(100, 'N', 'boundary', 'administrative', 100),
                                                                                                                   (145, 'N', 'boundary', 'administrative', 100),
                                                                                                                   (175, 'R', 'landcover', 'grass', 100)}
        assert self.temp_db_cursor.table_rows('import_polygon_delete') == 0
