# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for migration functions
"""
import pytest

from nominatim_db.tools import migration
from nominatim_db.errors import UsageError
import nominatim_db.version


class DummyTokenizer:

    def update_sql_functions(self, config):
        pass


@pytest.fixture
def postprocess_mock(monkeypatch):
    monkeypatch.setattr(migration.refresh, 'create_functions', lambda *args: args)
    monkeypatch.setattr(migration.tokenizer_factory, 'get_tokenizer_for_db',
                        lambda *args: DummyTokenizer())


def test_no_migration_old_versions(temp_db_with_extensions, def_config, property_table):
    property_table.set('database_version', '4.2.99-0')

    with pytest.raises(UsageError, match='Migration not possible'):
        migration.migrate(def_config, {})


def test_already_at_version(temp_db_with_extensions, def_config, property_table):

    property_table.set('database_version',
                       str(nominatim_db.version.NOMINATIM_VERSION))

    assert migration.migrate(def_config, {}) == 0


def test_run_single_migration(temp_db_with_extensions, def_config, temp_db_cursor,
                              property_table, monkeypatch, postprocess_mock):
    oldversion = [4, 4, 99, 0]
    property_table.set('database_version',
                       str(nominatim_db.version.NominatimVersion(*oldversion)))

    done = {'old': False, 'new': False}

    def _migration(**_):
        """ Dummy migration"""
        done['new'] = True

    def _old_migration(**_):
        """ Dummy migration"""
        done['old'] = True

    oldversion[1] = 0
    monkeypatch.setattr(migration, '_MIGRATION_FUNCTIONS',
                        [(tuple(oldversion), _old_migration),
                         (nominatim_db.version.NOMINATIM_VERSION, _migration)])

    assert migration.migrate(def_config, {}) == 0

    assert done['new']
    assert not done['old']
    assert property_table.get('database_version') == str(nominatim_db.version.NOMINATIM_VERSION)


# Tests for specific migrations
#
# Each migration should come with two tests:
#  1. Test that migration from old to new state works as expected.
#  2. Test that the migration can be rerun on the new state without side effects.
