# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for correctly assigning wikipedia pages to places.
"""
import gzip
import csv

import pytest

from nominatim.tools.refresh import import_wikipedia_articles, recompute_importance, create_functions

@pytest.fixture
def wiki_csv(tmp_path, sql_preprocessor):
    def _import(data):
        with gzip.open(tmp_path / 'wikimedia-importance.csv.gz', mode='wt') as fd:
            writer = csv.DictWriter(fd, fieldnames=['language', 'type', 'title',
                                                    'importance', 'wikidata_id'],
                                    delimiter='\t', quotechar='|')
            writer.writeheader()
            for lang, title, importance, wd in data:
                writer.writerow({'language': lang, 'type': 'a',
                                 'title': title, 'importance': str(importance),
                                 'wikidata_id' : wd})
        return tmp_path

    return _import


@pytest.mark.parametrize('extra', [{'wikipedia:en': 'Test'},
                                   {'wikipedia': 'en:Test'},
                                   {'wikidata': 'Q123'}])
def test_wikipedia(dsn, temp_db_conn, temp_db_cursor, def_config, wiki_csv, placex_table, extra):
    import_wikipedia_articles(dsn, wiki_csv([('en', 'Test', 0.3, 'Q123')]))
    create_functions(temp_db_conn, def_config)

    content = temp_db_cursor.row_set(
        'SELECT language, title, importance, wikidata FROM wikimedia_importance')
    assert content == set([('en', 'Test', 0.3, 'Q123')])

    placex_table.add(osm_id=12, extratags=extra)

    recompute_importance(temp_db_conn)

    content = temp_db_cursor.row_set('SELECT wikipedia, importance FROM placex')
    assert content == set([('en:Test', 0.3)])


def test_wikipedia_no_match(dsn, temp_db_conn, temp_db_cursor, def_config, wiki_csv,
                            placex_table):
    import_wikipedia_articles(dsn, wiki_csv([('de', 'Test', 0.3, 'Q123')]))
    create_functions(temp_db_conn, def_config)

    placex_table.add(osm_id=12, extratags={'wikipedia': 'en:Test'}, rank_search=10)

    recompute_importance(temp_db_conn)

    content = temp_db_cursor.row_set('SELECT wikipedia, importance FROM placex')
    assert list(content) == [(None, pytest.approx(0.26667666))]
