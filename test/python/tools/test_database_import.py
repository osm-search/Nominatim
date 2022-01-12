# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for functions to import a new database.
"""
from pathlib import Path
from contextlib import closing

import pytest
import psycopg2

from nominatim.tools import database_import
from nominatim.errors import UsageError

class TestDatabaseSetup:
    DBNAME = 'test_nominatim_python_unittest'

    @pytest.fixture(autouse=True)
    def setup_nonexistant_db(self):
        conn = psycopg2.connect(database='postgres')

        try:
            conn.set_isolation_level(0)
            with conn.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS {self.DBNAME}')

            yield True

            with conn.cursor() as cur:
                cur.execute(f'DROP DATABASE IF EXISTS {self.DBNAME}')
        finally:
            conn.close()

    @pytest.fixture
    def cursor(self):
        conn = psycopg2.connect(database=self.DBNAME)

        try:
            with conn.cursor() as cur:
                yield cur
        finally:
            conn.close()


    def conn(self):
        return closing(psycopg2.connect(database=self.DBNAME))


    def test_setup_skeleton(self):
        database_import.setup_database_skeleton(f'dbname={self.DBNAME}')

        # Check that all extensions are set up.
        with self.conn() as conn:
            with conn.cursor() as cur:
                cur.execute('CREATE TABLE t (h HSTORE, geom GEOMETRY(Geometry, 4326))')


    def test_unsupported_pg_version(self, monkeypatch):
        monkeypatch.setattr(database_import, 'POSTGRESQL_REQUIRED_VERSION', (100, 4))

        with pytest.raises(UsageError, match='PostgreSQL server is too old.'):
            database_import.setup_database_skeleton(f'dbname={self.DBNAME}')


    def test_create_db_explicit_ro_user(self):
        database_import.setup_database_skeleton(f'dbname={self.DBNAME}',
                                                rouser='postgres')


    def test_create_db_missing_ro_user(self):
        with pytest.raises(UsageError, match='Missing read-only user.'):
            database_import.setup_database_skeleton(f'dbname={self.DBNAME}',
                                                    rouser='sdfwkjkjgdugu2;jgsafkljas;')


    def test_setup_extensions_old_postgis(self, monkeypatch):
        monkeypatch.setattr(database_import, 'POSTGIS_REQUIRED_VERSION', (50, 50))

        with pytest.raises(UsageError, match='PostGIS is too old.'):
            database_import.setup_database_skeleton(f'dbname={self.DBNAME}')


def test_setup_skeleton_already_exists(temp_db):
    with pytest.raises(UsageError):
        database_import.setup_database_skeleton(f'dbname={temp_db}')


def test_import_osm_data_simple(table_factory, osm2pgsql_options, capfd):
    table_factory('place', content=((1, ), ))

    database_import.import_osm_data(Path('file.pbf'), osm2pgsql_options)
    captured = capfd.readouterr()

    assert '--create' in captured.out
    assert '--output gazetteer' in captured.out
    assert f'--style {osm2pgsql_options["osm2pgsql_style"]}' in captured.out
    assert f'--number-processes {osm2pgsql_options["threads"]}' in captured.out
    assert f'--cache {osm2pgsql_options["osm2pgsql_cache"]}' in captured.out
    assert 'file.pbf' in captured.out


def test_import_osm_data_multifile(table_factory, tmp_path, osm2pgsql_options, capfd):
    table_factory('place', content=((1, ), ))
    osm2pgsql_options['osm2pgsql_cache'] = 0

    files = [tmp_path / 'file1.osm', tmp_path / 'file2.osm']
    for f in files:
        f.write_text('test')

    database_import.import_osm_data(files, osm2pgsql_options)
    captured = capfd.readouterr()

    assert 'file1.osm' in captured.out
    assert 'file2.osm' in captured.out


def test_import_osm_data_simple_no_data(table_factory, osm2pgsql_options):
    table_factory('place')

    with pytest.raises(UsageError, match='No data imported'):
        database_import.import_osm_data(Path('file.pbf'), osm2pgsql_options)


def test_import_osm_data_simple_ignore_no_data(table_factory, osm2pgsql_options):
    table_factory('place')

    database_import.import_osm_data(Path('file.pbf'), osm2pgsql_options,
                                    ignore_errors=True)


def test_import_osm_data_drop(table_factory, temp_db_conn, tmp_path, osm2pgsql_options):
    table_factory('place', content=((1, ), ))
    table_factory('planet_osm_nodes')

    flatfile = tmp_path / 'flatfile'
    flatfile.write_text('touch')

    osm2pgsql_options['flatnode_file'] = str(flatfile.resolve())

    database_import.import_osm_data(Path('file.pbf'), osm2pgsql_options, drop=True)

    assert not flatfile.exists()
    assert not temp_db_conn.table_exists('planet_osm_nodes')


def test_import_osm_data_default_cache(table_factory, osm2pgsql_options, capfd):
    table_factory('place', content=((1, ), ))

    osm2pgsql_options['osm2pgsql_cache'] = 0

    database_import.import_osm_data(Path(__file__), osm2pgsql_options)
    captured = capfd.readouterr()

    assert f'--cache {osm2pgsql_options["osm2pgsql_cache"]}' in captured.out


@pytest.mark.parametrize("with_search", (True, False))
def test_truncate_database_tables(temp_db_conn, temp_db_cursor, table_factory, with_search):
    tables = ['placex', 'place_addressline', 'location_area',
              'location_area_country',
              'location_property_tiger', 'location_property_osmline',
              'location_postcode', 'location_road_23']
    if with_search:
        tables.append('search_name')

    for table in tables:
        table_factory(table, content=((1, ), (2, ), (3, )))
        assert temp_db_cursor.table_rows(table) == 3

    database_import.truncate_data_tables(temp_db_conn)

    for table in tables:
        assert temp_db_cursor.table_rows(table) == 0


@pytest.mark.parametrize("threads", (1, 5))
def test_load_data(dsn, place_row, placex_table, osmline_table,
                   word_table, temp_db_cursor, threads):
    for func in ('precompute_words', 'getorcreate_housenumber_id', 'make_standard_name'):
        temp_db_cursor.execute(f"""CREATE FUNCTION {func} (src TEXT)
                                  RETURNS TEXT AS $$ SELECT 'a'::TEXT $$ LANGUAGE SQL
                               """)
    for oid in range(100, 130):
        place_row(osm_id=oid)
    place_row(osm_type='W', osm_id=342, cls='place', typ='houses',
              geom='SRID=4326;LINESTRING(0 0, 10 10)')

    database_import.load_data(dsn, threads)

    assert temp_db_cursor.table_rows('placex') == 30
    assert temp_db_cursor.table_rows('location_property_osmline') == 1


class TestSetupSQL:

    @pytest.fixture(autouse=True)
    def init_env(self, temp_db, tmp_path, def_config, sql_preprocessor_cfg):
        def_config.lib_dir.sql = tmp_path / 'sql'
        def_config.lib_dir.sql.mkdir()

        self.config = def_config


    def write_sql(self, fname, content):
        (self.config.lib_dir.sql / fname).write_text(content)


    @pytest.mark.parametrize("reverse", [True, False])
    def test_create_tables(self, temp_db_conn, temp_db_cursor, reverse):
        self.write_sql('tables.sql',
                       """CREATE FUNCTION test() RETURNS bool
                          AS $$ SELECT {{db.reverse_only}} $$ LANGUAGE SQL""")

        database_import.create_tables(temp_db_conn, self.config, reverse)

        temp_db_cursor.scalar('SELECT test()') == reverse


    def test_create_table_triggers(self, temp_db_conn, temp_db_cursor):
        self.write_sql('table-triggers.sql',
                       """CREATE FUNCTION test() RETURNS TEXT
                          AS $$ SELECT 'a'::text $$ LANGUAGE SQL""")

        database_import.create_table_triggers(temp_db_conn, self.config)

        temp_db_cursor.scalar('SELECT test()') == 'a'


    def test_create_partition_tables(self, temp_db_conn, temp_db_cursor):
        self.write_sql('partition-tables.src.sql',
                       """CREATE FUNCTION test() RETURNS TEXT
                          AS $$ SELECT 'b'::text $$ LANGUAGE SQL""")

        database_import.create_partition_tables(temp_db_conn, self.config)

        temp_db_cursor.scalar('SELECT test()') == 'b'


    @pytest.mark.parametrize("drop", [True, False])
    def test_create_search_indices(self, temp_db_conn, temp_db_cursor, drop):
        self.write_sql('indices.sql',
                       """CREATE FUNCTION test() RETURNS bool
                          AS $$ SELECT {{drop}} $$ LANGUAGE SQL""")

        database_import.create_search_indices(temp_db_conn, self.config, drop)

        temp_db_cursor.scalar('SELECT test()') == drop
