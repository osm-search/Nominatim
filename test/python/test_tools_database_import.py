"""
Tests for functions to import a new database.
"""
import pytest
import psycopg2
import sys
from pathlib import Path

from nominatim.tools import database_import
from nominatim.errors import UsageError

@pytest.fixture
def nonexistant_db():
    dbname = 'test_nominatim_python_unittest'

    conn = psycopg2.connect(database='postgres')

    conn.set_isolation_level(0)
    with conn.cursor() as cur:
        cur.execute('DROP DATABASE IF EXISTS {}'.format(dbname))

    yield dbname

    with conn.cursor() as cur:
        cur.execute('DROP DATABASE IF EXISTS {}'.format(dbname))

@pytest.mark.parametrize("no_partitions", (True, False))
def test_setup_skeleton(src_dir, nonexistant_db, no_partitions):
    database_import.setup_database_skeleton('dbname=' + nonexistant_db,
                                            src_dir / 'data', no_partitions)

    conn = psycopg2.connect(database=nonexistant_db)

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT distinct partition FROM country_name")
            partitions = set([r[0] for r in list(cur)])
            if no_partitions:
                assert partitions == set([0])
            else:
                assert len(partitions) > 10
    finally:
        conn.close()


def test_create_db_success(nonexistant_db):
    database_import.create_db('dbname=' + nonexistant_db, rouser='www-data')

    conn = psycopg2.connect(database=nonexistant_db)
    conn.close()


def test_create_db_already_exists(temp_db):
    with pytest.raises(UsageError):
        database_import.create_db('dbname=' + temp_db)


def test_create_db_unsupported_version(nonexistant_db, monkeypatch):
    monkeypatch.setattr(database_import, 'POSTGRESQL_REQUIRED_VERSION', (100, 4))

    with pytest.raises(UsageError, match='PostgreSQL server is too old.'):
        database_import.create_db('dbname=' + nonexistant_db)


def test_create_db_missing_ro_user(nonexistant_db):
    with pytest.raises(UsageError, match='Missing read-only user.'):
        database_import.create_db('dbname=' + nonexistant_db, rouser='sdfwkjkjgdugu2;jgsafkljas;')


def test_setup_extensions(temp_db_conn, temp_db_cursor):
    database_import.setup_extensions(temp_db_conn)

    temp_db_cursor.execute('CREATE TABLE t (h HSTORE, geom GEOMETRY(Geometry, 4326))')


def test_setup_extensions_old_postgis(temp_db_conn, monkeypatch):
    monkeypatch.setattr(database_import, 'POSTGIS_REQUIRED_VERSION', (50, 50))

    with pytest.raises(UsageError, match='PostGIS version is too old.'):
        database_import.setup_extensions(temp_db_conn)


def test_install_module(tmp_path):
    src_dir = tmp_path / 'source'
    src_dir.mkdir()
    (src_dir / 'nominatim.so').write_text('TEST nomiantim.so')

    project_dir = tmp_path / 'project'
    project_dir.mkdir()

    database_import.install_module(src_dir, project_dir, '')

    outfile = project_dir / 'module' / 'nominatim.so'

    assert outfile.exists()
    assert outfile.read_text() == 'TEST nomiantim.so'
    assert outfile.stat().st_mode == 33261


def test_install_module_custom(tmp_path):
    (tmp_path / 'nominatim.so').write_text('TEST nomiantim.so')

    database_import.install_module(tmp_path, tmp_path, str(tmp_path.resolve()))

    assert not (tmp_path / 'module').exists()


def test_install_module_fail_access(temp_db_conn, tmp_path):
    (tmp_path / 'nominatim.so').write_text('TEST nomiantim.so')

    with pytest.raises(UsageError, match='.*module cannot be accessed.*'):
        database_import.install_module(tmp_path, tmp_path, '',
                                       conn=temp_db_conn)


def test_import_base_data(src_dir, temp_db, temp_db_cursor):
    temp_db_cursor.execute('CREATE EXTENSION hstore')
    temp_db_cursor.execute('CREATE EXTENSION postgis')
    database_import.import_base_data('dbname=' + temp_db, src_dir / 'data')

    assert temp_db_cursor.scalar('SELECT count(*) FROM country_name') > 0


def test_import_base_data_ignore_partitions(src_dir, temp_db, temp_db_cursor):
    temp_db_cursor.execute('CREATE EXTENSION hstore')
    temp_db_cursor.execute('CREATE EXTENSION postgis')
    database_import.import_base_data('dbname=' + temp_db, src_dir / 'data',
                                     ignore_partitions=True)

    assert temp_db_cursor.scalar('SELECT count(*) FROM country_name') > 0
    assert temp_db_cursor.scalar('SELECT count(*) FROM country_name WHERE partition != 0') == 0


def test_import_osm_data_simple(temp_db_cursor,osm2pgsql_options):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    temp_db_cursor.execute('INSERT INTO place values (1)')

    database_import.import_osm_data('file.pdf', osm2pgsql_options)


def test_import_osm_data_simple_no_data(temp_db_cursor,osm2pgsql_options):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')

    with pytest.raises(UsageError, match='No data.*'):
        database_import.import_osm_data('file.pdf', osm2pgsql_options)


def test_import_osm_data_drop(temp_db_conn, temp_db_cursor, tmp_path, osm2pgsql_options):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    temp_db_cursor.execute('CREATE TABLE planet_osm_nodes (id INT)')
    temp_db_cursor.execute('INSERT INTO place values (1)')

    flatfile = tmp_path / 'flatfile'
    flatfile.write_text('touch')

    osm2pgsql_options['flatnode_file'] = str(flatfile.resolve())

    database_import.import_osm_data('file.pdf', osm2pgsql_options, drop=True)

    assert not flatfile.exists()
    assert not temp_db_conn.table_exists('planet_osm_nodes')


def test_import_osm_data_default_cache(temp_db_cursor,osm2pgsql_options):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    temp_db_cursor.execute('INSERT INTO place values (1)')

    osm2pgsql_options['osm2pgsql_cache'] = 0

    database_import.import_osm_data(Path(__file__), osm2pgsql_options)


def test_truncate_database_tables(temp_db_conn, temp_db_cursor, table_factory):
    tables = ('word', 'placex', 'place_addressline', 'location_area',
              'location_area_country', 'location_property',
              'location_property_tiger', 'location_property_osmline',
              'location_postcode', 'search_name', 'location_road_23')
    for table in tables:
        table_factory(table, content=(1, 2, 3))

    database_import.truncate_data_tables(temp_db_conn, max_word_frequency=23)

    for table in tables:
        assert temp_db_cursor.table_rows(table) == 0


@pytest.mark.parametrize("threads", (1, 5))
def test_load_data(dsn, src_dir, place_row, placex_table, osmline_table, word_table,
                   temp_db_cursor, threads):
    for func in ('make_keywords', 'getorcreate_housenumber_id', 'make_standard_name'):
        temp_db_cursor.execute("""CREATE FUNCTION {} (src TEXT)
                                  RETURNS TEXT AS $$ SELECT 'a'::TEXT $$ LANGUAGE SQL
                               """.format(func))
    for oid in range(100, 130):
        place_row(osm_id=oid)
    place_row(osm_type='W', osm_id=342, cls='place', typ='houses',
              geom='SRID=4326;LINESTRING(0 0, 10 10)')

    database_import.load_data(dsn, src_dir / 'data', threads)

    assert temp_db_cursor.table_rows('placex') == 30
    assert temp_db_cursor.table_rows('location_property_osmline') == 1

@pytest.mark.parametrize("languages", (False, True))
def test_create_country_names(temp_db_conn, temp_db_cursor, def_config,
                              temp_db_with_extensions, monkeypatch, languages):
    if languages:
        monkeypatch.setenv('NOMINATIM_LANGUAGES', 'fr,en')
    temp_db_cursor.execute("""CREATE FUNCTION make_standard_name (name TEXT)
                                  RETURNS TEXT AS $$ SELECT 'a'::TEXT $$ LANGUAGE SQL
                               """)
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_country(lookup_word TEXT,
                                               lookup_country_code varchar(2))
                            RETURNS INTEGER
                            AS $$
                            BEGIN
                                INSERT INTO country_name VALUES (5, lookup_word);
                                RETURN 5;
                            END;
                            $$
                            LANGUAGE plpgsql;
                               """)
    temp_db_cursor.execute('CREATE TABLE country_name (id int, country_code varchar(2), name hstore)')
    database_import.create_country_names(temp_db_conn, def_config)
    assert temp_db_cursor.table_rows('country_name') == 4
