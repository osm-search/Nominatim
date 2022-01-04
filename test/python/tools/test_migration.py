# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for migration functions
"""
import pytest
import psycopg2.extras

from nominatim.tools import migration
from nominatim.errors import UsageError
import nominatim.version

class DummyTokenizer:

    def update_sql_functions(self, config):
        pass


@pytest.fixture
def postprocess_mock(monkeypatch):
    monkeypatch.setattr(migration.refresh, 'create_functions', lambda *args: args)
    monkeypatch.setattr(migration.tokenizer_factory, 'get_tokenizer_for_db',
                        lambda *args: DummyTokenizer())


def test_no_migration_old_versions(temp_db_with_extensions, table_factory, def_config):
    table_factory('country_name', 'name HSTORE, country_code TEXT')

    with pytest.raises(UsageError, match='Migration not possible'):
        migration.migrate(def_config, {})


def test_set_up_migration_for_36(temp_db_with_extensions, temp_db_cursor,
                                 table_factory, def_config, monkeypatch,
                                 postprocess_mock):
    psycopg2.extras.register_hstore(temp_db_cursor)
    # don't actually run any migration, except the property table creation
    monkeypatch.setattr(migration, '_MIGRATION_FUNCTIONS',
                        [((3, 5, 0, 99), migration.add_nominatim_property_table)])
    # Use a r/o user name that always exists
    monkeypatch.setenv('NOMINATIM_DATABASE_WEBUSER', 'postgres')

    table_factory('country_name', 'name HSTORE, country_code TEXT',
                  (({str(x): 'a' for x in range(200)}, 'gb'),))

    assert not temp_db_cursor.table_exists('nominatim_properties')

    assert migration.migrate(def_config, {}) == 0

    assert temp_db_cursor.table_exists('nominatim_properties')

    assert 1 == temp_db_cursor.scalar(""" SELECT count(*) FROM nominatim_properties
                                          WHERE property = 'database_version'""")


def test_already_at_version(def_config, property_table):

    property_table.set('database_version',
                       '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(nominatim.version.NOMINATIM_VERSION))

    assert migration.migrate(def_config, {}) == 0


def test_no_migrations_necessary(def_config, temp_db_cursor, property_table,
                                 monkeypatch):
    oldversion = [x for x in nominatim.version.NOMINATIM_VERSION]
    oldversion[0] -= 1
    property_table.set('database_version',
                       '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(oldversion))

    oldversion[0] = 0
    monkeypatch.setattr(migration, '_MIGRATION_FUNCTIONS',
                        [(tuple(oldversion), lambda **attr: True)])

    assert migration.migrate(def_config, {}) == 0


def test_run_single_migration(def_config, temp_db_cursor, property_table,
                              monkeypatch, postprocess_mock):
    oldversion = [x for x in nominatim.version.NOMINATIM_VERSION]
    oldversion[0] -= 1
    property_table.set('database_version',
                       '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(oldversion))

    done = {'old': False, 'new': False}
    def _migration(**_):
        """ Dummy migration"""
        done['new'] = True

    def _old_migration(**_):
        """ Dummy migration"""
        done['old'] = True

    oldversion[0] = 0
    monkeypatch.setattr(migration, '_MIGRATION_FUNCTIONS',
                        [(tuple(oldversion), _old_migration),
                         (nominatim.version.NOMINATIM_VERSION, _migration)])

    assert migration.migrate(def_config, {}) == 0

    assert done['new']
    assert not done['old']
    assert property_table.get('database_version') == \
           '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(nominatim.version.NOMINATIM_VERSION)


###### Tests for specific migrations
#
# Each migration should come with two tests:
#  1. Test that migration from old to new state works as expected.
#  2. Test that the migration can be rerun on the new state without side effects.


@pytest.mark.parametrize('in_attr', ('', 'with time zone'))
def test_import_status_timestamp_change(temp_db_conn, temp_db_cursor,
                                        table_factory, in_attr):
    table_factory('import_status',
                  f"""lastimportdate timestamp {in_attr},
                     sequence_id integer,
                     indexed boolean""")

    migration.import_status_timestamp_change(temp_db_conn)
    temp_db_conn.commit()

    assert temp_db_cursor.scalar("""SELECT data_type FROM information_schema.columns
                                    WHERE table_name = 'import_status'
                                      and column_name = 'lastimportdate'""")\
            == 'timestamp with time zone'


def test_add_nominatim_property_table(temp_db_conn, temp_db_cursor,
                                      def_config, monkeypatch):
    # Use a r/o user name that always exists
    monkeypatch.setenv('NOMINATIM_DATABASE_WEBUSER', 'postgres')

    assert not temp_db_cursor.table_exists('nominatim_properties')

    migration.add_nominatim_property_table(temp_db_conn, def_config)
    temp_db_conn.commit()

    assert temp_db_cursor.table_exists('nominatim_properties')


def test_add_nominatim_property_table_repeat(temp_db_conn, temp_db_cursor,
                                             def_config, property_table):
    assert temp_db_cursor.table_exists('nominatim_properties')

    migration.add_nominatim_property_table(temp_db_conn, def_config)
    temp_db_conn.commit()

    assert temp_db_cursor.table_exists('nominatim_properties')


def test_change_housenumber_transliteration(temp_db_conn, temp_db_cursor,
                                            word_table, placex_table):
    placex_table.add(housenumber='3A')

    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION make_standard_name(name TEXT)
                              RETURNS TEXT AS $$ SELECT lower(name) $$ LANGUAGE SQL """)
    temp_db_cursor.execute("""CREATE OR REPLACE FUNCTION getorcreate_housenumber_id(lookup_word TEXT)
                              RETURNS INTEGER AS $$ SELECT 4325 $$ LANGUAGE SQL """)

    migration.change_housenumber_transliteration(temp_db_conn)
    temp_db_conn.commit()

    assert temp_db_cursor.scalar('SELECT housenumber from placex') == '3a'

    migration.change_housenumber_transliteration(temp_db_conn)
    temp_db_conn.commit()

    assert temp_db_cursor.scalar('SELECT housenumber from placex') == '3a'


def test_switch_placenode_geometry_index(temp_db_conn, temp_db_cursor, placex_table):
    temp_db_cursor.execute("""CREATE INDEX idx_placex_adminname
                              ON placex (place_id)""")

    migration.switch_placenode_geometry_index(temp_db_conn)
    temp_db_conn.commit()

    assert temp_db_cursor.index_exists('placex', 'idx_placex_geometry_placenode')
    assert not temp_db_cursor.index_exists('placex', 'idx_placex_adminname')


def test_switch_placenode_geometry_index_repeat(temp_db_conn, temp_db_cursor, placex_table):
    temp_db_cursor.execute("""CREATE INDEX idx_placex_geometry_placenode
                              ON placex (place_id)""")

    migration.switch_placenode_geometry_index(temp_db_conn)
    temp_db_conn.commit()

    assert temp_db_cursor.index_exists('placex', 'idx_placex_geometry_placenode')
    assert not temp_db_cursor.index_exists('placex', 'idx_placex_adminname')
    assert temp_db_cursor.scalar("""SELECT indexdef from pg_indexes
                                    WHERE tablename = 'placex'
                                      and indexname = 'idx_placex_geometry_placenode'
                                 """).endswith('(place_id)')


def test_install_legacy_tokenizer(temp_db_conn, temp_db_cursor, project_env,
                                  property_table, table_factory, monkeypatch,
                                  tmp_path):
    table_factory('placex', 'place_id BIGINT')
    table_factory('location_property_osmline', 'place_id BIGINT')

    # Setting up the tokenizer is problematic
    class MiniTokenizer:
        def migrate_database(self, config):
            pass

    monkeypatch.setattr(migration.tokenizer_factory, 'create_tokenizer',
                        lambda cfg, **kwargs: MiniTokenizer())

    migration.install_legacy_tokenizer(temp_db_conn, project_env)
    temp_db_conn.commit()



def test_install_legacy_tokenizer_repeat(temp_db_conn, temp_db_cursor,
                                         def_config, property_table):

    property_table.set('tokenizer', 'dummy')
    migration.install_legacy_tokenizer(temp_db_conn, def_config)
    temp_db_conn.commit()


def test_create_tiger_housenumber_index(temp_db_conn, temp_db_cursor, table_factory):
    table_factory('location_property_tiger',
                  'parent_place_id BIGINT, startnumber INT, endnumber INT')

    migration.create_tiger_housenumber_index(temp_db_conn)
    temp_db_conn.commit()

    if temp_db_conn.server_version_tuple() >= (11, 0, 0):
        assert temp_db_cursor.index_exists('location_property_tiger',
                                           'idx_location_property_tiger_housenumber_migrated')

    migration.create_tiger_housenumber_index(temp_db_conn)
    temp_db_conn.commit()
