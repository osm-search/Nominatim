# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for maintenance and analysis functions.
"""
import pytest
import datetime as dt

from nominatim_db.errors import UsageError
from nominatim_db.tools import admin
from nominatim_db.tokenizer import factory
from nominatim_db.db.sql_preprocessor import SQLPreprocessor


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


def test_analyse_indexing_with_place_id(project_env, placex_row):
    place_id = placex_row()

    admin.analyse_indexing(project_env, place_id=place_id)


def test_analyse_indexing_with_osm_id(project_env, placex_row):
    placex_row(osm_type='N', osm_id=10000)

    admin.analyse_indexing(project_env, osm_id='N10000')


class TestAdminCleanDeleted:

    @pytest.fixture(autouse=True)
    def setup_polygon_delete(self, project_env, table_factory, place_table, placex_row,
                             osmline_table, temp_db_cursor, temp_db_conn, def_config, src_dir):
        """ Set up place_force_delete function and related tables
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

        now = dt.datetime.now()
        placex_row(osm_type='N', osm_id=100, cls='boundary', typ='administrative',
                   indexed_status=1, indexed_date=now - dt.timedelta(days=30))
        placex_row(osm_type='N', osm_id=145, cls='boundary', typ='administrative',
                   indexed_status=1, indexed_date=now - dt.timedelta(days=90))
        placex_row(osm_type='R', osm_id=175, cls='landcover', typ='grass',
                   indexed_status=1, indexed_date=now - dt.timedelta(days=90))

        # set up tables and triggers for utils function
        table_factory('place_to_be_deleted',
                      """osm_id BIGINT,
                      osm_type CHAR(1),
                      class TEXT NOT NULL,
                      type TEXT NOT NULL,
                      deferred BOOLEAN""")
        table_factory('import_polygon_error', """osm_id BIGINT,
                      osm_type CHAR(1),
                      class TEXT NOT NULL,
                      type TEXT NOT NULL""")
        temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION place_delete()
                               RETURNS TRIGGER AS $$
                               BEGIN RETURN NULL; END;
                               $$ LANGUAGE plpgsql;""")
        temp_db_cursor.execute("""CREATE TRIGGER place_before_delete BEFORE DELETE ON place
                               FOR EACH ROW EXECUTE PROCEDURE place_delete();""")
        orig_sql = def_config.lib_dir.sql
        def_config.lib_dir.sql = src_dir / 'lib-sql'
        sqlproc = SQLPreprocessor(temp_db_conn, def_config)
        sqlproc.run_sql_file(temp_db_conn, 'functions/utils.sql')
        def_config.lib_dir.sql = orig_sql

    def test_admin_clean_deleted_no_records(self):
        admin.clean_deleted_relations(self.project_env, age='1 year')

        rowset = self.temp_db_cursor.row_set(
            'SELECT osm_id, osm_type, class, type, indexed_status FROM placex')

        assert rowset == {(100, 'N', 'boundary', 'administrative', 1),
                          (145, 'N', 'boundary', 'administrative', 1),
                          (175, 'R', 'landcover', 'grass', 1)}
        assert self.temp_db_cursor.table_rows('import_polygon_delete') == 3

    @pytest.mark.parametrize('test_age', ['T week', '1 welk', 'P1E'])
    def test_admin_clean_deleted_bad_age(self, test_age):
        with pytest.raises(UsageError):
            admin.clean_deleted_relations(self.project_env, age=test_age)

    def test_admin_clean_deleted_partial(self):
        admin.clean_deleted_relations(self.project_env, age='2 months')

        rowset = self.temp_db_cursor.row_set(
            'SELECT osm_id, osm_type, class, type, indexed_status FROM placex')

        assert rowset == {(100, 'N', 'boundary', 'administrative', 1),
                          (145, 'N', 'boundary', 'administrative', 100),
                          (175, 'R', 'landcover', 'grass', 100)}
        assert self.temp_db_cursor.table_rows('import_polygon_delete') == 1

    @pytest.mark.parametrize('test_age', ['1 week', 'P3D', '5 hours'])
    def test_admin_clean_deleted(self, test_age):
        admin.clean_deleted_relations(self.project_env, age=test_age)

        rowset = self.temp_db_cursor.row_set(
            'SELECT osm_id, osm_type, class, type, indexed_status FROM placex')

        assert rowset == {(100, 'N', 'boundary', 'administrative', 100),
                          (145, 'N', 'boundary', 'administrative', 100),
                          (175, 'R', 'landcover', 'grass', 100)}
        assert self.temp_db_cursor.table_rows('import_polygon_delete') == 0
