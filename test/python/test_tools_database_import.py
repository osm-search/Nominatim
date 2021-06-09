"""
Tests for functions to import a new database.
"""
from pathlib import Path

import pytest
import psycopg2

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
            partitions = set((r[0] for r in list(cur)))
            if no_partitions:
                assert partitions == set((0, ))
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


def test_setup_extensions(temp_db_conn, table_factory):
    database_import.setup_extensions(temp_db_conn)

    # Use table creation to check that hstore and geometry types are available.
    table_factory('t', 'h HSTORE, geom GEOMETRY(Geometry, 4326)')


def test_setup_extensions_old_postgis(temp_db_conn, monkeypatch):
    monkeypatch.setattr(database_import, 'POSTGIS_REQUIRED_VERSION', (50, 50))

    with pytest.raises(UsageError, match='PostGIS version is too old.'):
        database_import.setup_extensions(temp_db_conn)


def test_import_base_data(dsn, src_dir, temp_db_with_extensions, temp_db_cursor):
    database_import.import_base_data(dsn, src_dir / 'data')

    assert temp_db_cursor.table_rows('country_name') > 0


def test_import_base_data_ignore_partitions(dsn, src_dir, temp_db_with_extensions,
                                            temp_db_cursor):
    database_import.import_base_data(dsn, src_dir / 'data', ignore_partitions=True)

    assert temp_db_cursor.table_rows('country_name') > 0
    assert temp_db_cursor.table_rows('country_name', where='partition != 0') == 0


def test_import_osm_data_simple(table_factory, osm2pgsql_options):
    table_factory('place', content=((1, ), ))

    database_import.import_osm_data('file.pdf', osm2pgsql_options)


def test_import_osm_data_simple_no_data(table_factory, osm2pgsql_options):
    table_factory('place')

    with pytest.raises(UsageError, match='No data.*'):
        database_import.import_osm_data('file.pdf', osm2pgsql_options)


def test_import_osm_data_drop(table_factory, temp_db_conn, tmp_path, osm2pgsql_options):
    table_factory('place', content=((1, ), ))
    table_factory('planet_osm_nodes')

    flatfile = tmp_path / 'flatfile'
    flatfile.write_text('touch')

    osm2pgsql_options['flatnode_file'] = str(flatfile.resolve())

    database_import.import_osm_data('file.pdf', osm2pgsql_options, drop=True)

    assert not flatfile.exists()
    assert not temp_db_conn.table_exists('planet_osm_nodes')


def test_import_osm_data_default_cache(table_factory, osm2pgsql_options):
    table_factory('place', content=((1, ), ))

    osm2pgsql_options['osm2pgsql_cache'] = 0

    database_import.import_osm_data(Path(__file__), osm2pgsql_options)


def test_truncate_database_tables(temp_db_conn, temp_db_cursor, table_factory):
    tables = ('placex', 'place_addressline', 'location_area',
              'location_area_country',
              'location_property_tiger', 'location_property_osmline',
              'location_postcode', 'search_name', 'location_road_23')
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
        temp_db_cursor.execute("""CREATE FUNCTION {} (src TEXT)
                                  RETURNS TEXT AS $$ SELECT 'a'::TEXT $$ LANGUAGE SQL
                               """.format(func))
    for oid in range(100, 130):
        place_row(osm_id=oid)
    place_row(osm_type='W', osm_id=342, cls='place', typ='houses',
              geom='SRID=4326;LINESTRING(0 0, 10 10)')

    database_import.load_data(dsn, threads)

    assert temp_db_cursor.table_rows('placex') == 30
    assert temp_db_cursor.table_rows('location_property_osmline') == 1


@pytest.mark.parametrize("languages", (None, ' fr,en'))
def test_create_country_names(temp_db_with_extensions, temp_db_conn, temp_db_cursor,
                              table_factory, tokenizer_mock, languages):

    table_factory('country_name', 'country_code varchar(2), name hstore',
                  content=(('us', '"name"=>"us1","name:af"=>"us2"'),
                           ('fr', '"name"=>"Fra", "name:en"=>"Fren"')))

    assert temp_db_cursor.scalar("SELECT count(*) FROM country_name") == 2

    tokenizer = tokenizer_mock()

    database_import.create_country_names(temp_db_conn, tokenizer, languages)

    assert len(tokenizer.analyser_cache['countries']) == 2

    result_set = {k: set(v.values()) for k, v in tokenizer.analyser_cache['countries']}

    if languages:
        assert result_set == {'us' : set(('us', 'us1', 'United States')),
                              'fr' : set(('fr', 'Fra', 'Fren'))}
    else:
        assert result_set == {'us' : set(('us', 'us1', 'us2', 'United States')),
                              'fr' : set(('fr', 'Fra', 'Fren'))}
