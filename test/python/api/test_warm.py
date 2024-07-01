# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for warm-up CLI function.
"""
import pytest

import nominatim_db.cli

@pytest.fixture(autouse=True)
def setup_database_with_context(apiobj, table_factory):
    table_factory('word',
                  definition='word_id INT, word_token TEXT, type TEXT, word TEXT, info JSONB',
                  content=[(55, 'test', 'W', 'test', None),
                           (2, 'test', 'w', 'test', None)])

    apiobj.add_data('properties',
                    [{'property': 'tokenizer', 'value': 'icu'},
                     {'property': 'tokenizer_import_normalisation', 'value': ':: lower();'},
                     {'property': 'tokenizer_import_transliteration', 'value': "'1' > '/1/'; 'ä' > 'ä '"},
                    ])


@pytest.mark.parametrize('args', [['--search-only'], ['--reverse-only']])
def test_warm_all(tmp_path, args):
    assert 0 == nominatim_db.cli.nominatim(module_dir='MODULE NOT AVAILABLE',
                                           osm2pgsql_path='OSM2PGSQL NOT AVAILABLE',
                                           cli_args=['admin', '--project-dir', str(tmp_path),
                                                     '--warm'] + args)
