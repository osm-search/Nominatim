# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for function that handle country properties.
"""
from textwrap import dedent
import pytest

from nominatim.tools import country_info

@pytest.fixture
def loaded_country(def_config):
    country_info.setup_country_config(def_config)


@pytest.fixture
def env_with_country_config(project_env):

    def _mk_config(cfg):
        (project_env.project_dir / 'country_settings.yaml').write_text(dedent(cfg))

        return project_env

    return _mk_config


@pytest.mark.parametrize("no_partitions", (True, False))
def test_setup_country_tables(src_dir, temp_db_with_extensions, dsn, temp_db_cursor,
                              loaded_country, no_partitions):
    country_info.setup_country_tables(dsn, src_dir / 'data', no_partitions)

    assert temp_db_cursor.table_exists('country_name')
    assert temp_db_cursor.table_rows('country_name') == \
        temp_db_cursor.scalar(
            'SELECT count(DISTINCT country_code) FROM country_name')

    partitions = temp_db_cursor.row_set(
        "SELECT DISTINCT partition FROM country_name")
    if no_partitions:
        assert partitions == {(0, )}
    else:
        assert len(partitions) > 10

    assert temp_db_cursor.table_exists('country_osm_grid')
    assert temp_db_cursor.table_rows('country_osm_grid') > 100


@pytest.mark.parametrize("languages", (None, ['fr', 'en']))
def test_create_country_names(temp_db_with_extensions, temp_db_conn, temp_db_cursor,
                              table_factory, tokenizer_mock, languages, loaded_country):

    table_factory('country_name', 'country_code varchar(2), name hstore',
                  content=(('us', '"name"=>"us1","name:af"=>"us2"'),
                           ('fr', '"name"=>"Fra", "name:en"=>"Fren"')))

    assert temp_db_cursor.scalar("SELECT count(*) FROM country_name") == 2

    tokenizer = tokenizer_mock()

    country_info.create_country_names(temp_db_conn, tokenizer, languages)

    assert len(tokenizer.analyser_cache['countries']) == 2

    result_set = {k: set(v.values())
                  for k, v in tokenizer.analyser_cache['countries']}

    if languages:
        assert result_set == {'us': set(('us', 'us1')),
                              'fr': set(('fr', 'Fra', 'Fren'))}
    else:
        assert result_set == {'us': set(('us', 'us1', 'us2')),
                              'fr': set(('fr', 'Fra', 'Fren'))}


def test_setup_country_names_prefixes(env_with_country_config):
    config = env_with_country_config("""\
                                     es:
                                       names:
                                         name:
                                           en: Spain
                                           de: Spanien
                                           default: Espagñe
                                     us:
                                       names:
                                         short_name:
                                           default: USA
                                         name:
                                           default: United States
                                           en: United States
                                     """)
    info = country_info._CountryInfo()
    info.load(config)

    assert info.get('es')['names'] == {"name": "Espagñe",
                                       "name:en": "Spain",
                                       "name:de": "Spanien"}
    assert info.get('us')['names'] == {"name": "United States",
                                       "name:en": "United States",
                                       "short_name": "USA"}
    assert 'names' not in info.get('xx')


def test_setup_country_config_languages_not_loaded(env_with_country_config):
    config = env_with_country_config("""\
                                     de:
                                         partition: 3
                                         names:
                                             name:
                                                 default: Deutschland
                                     """)
    info = country_info._CountryInfo()
    info.load(config)
    assert dict(info.items()) == {'de': {'partition': 3,
                                  'languages': [],
                                  'names': {'name': 'Deutschland'}}}


def test_setup_country_config_name_not_loaded(env_with_country_config):
    config = env_with_country_config("""\
                                     de:
                                         partition: 3
                                         languages: de
                                         names:
                                     """)

    info = country_info._CountryInfo()
    info.load(config)

    assert dict(info.items()) == {'de': {'partition': 3,
                                         'languages': ['de'],
                                         'names': {}
                                 }}


def test_setup_country_config_names_not_loaded(env_with_country_config):
    config = env_with_country_config("""
                                     de:
                                         partition: 3
                                         languages: de
                                     """)

    info = country_info._CountryInfo()
    info.load(config)

    assert dict(info.items()) == {'de': {'partition': 3,
                                         'languages': ['de'],
                                         'names': {}
                                 }}


def test_setup_country_config_special_character(env_with_country_config):
    config = env_with_country_config("""
                                     bq:
                                         partition: 250
                                         languages: nl
                                         names: 
                                             name: 
                                                 default: "\\N"
                                     """)

    info = country_info._CountryInfo()
    info.load(config)

    assert dict(info.items()) == {'bq': {'partition': 250,
                                         'languages': ['nl'],
                                         'names': {'name': '\x85'}
                                 }}
