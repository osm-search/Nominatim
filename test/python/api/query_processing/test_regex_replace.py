# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
'''
Tests for replacing values in an input using custom regex.
'''
import pytest

import nominatim_api.search.query as qmod
from nominatim_api.query_preprocessing.config import QueryConfig
from nominatim_api.query_preprocessing import regex_replace


def run_preprocessor_on(query):
    config = QueryConfig()
    config.set_normalizer(None)

    config['replacements'] = [
        {'pattern': r'\b(?:\d{1,3}\.){3}\d{1,3}\b', 'replace': ''},  # IPv4
        {'pattern': r'https?://\S+', 'replace': ''}  # HTTP/HTTPS URLs
    ]

    proc = regex_replace.create(config)
    return proc(query)


@pytest.mark.parametrize('inp,outp', [
    (['45.67.89.101'], []),
    (['198.51.100.23'], []),
    (['203.0.113.255'], []),
    (['http://www.openstreetmap.org'], []),
    (['https://www.openstreetmap.org/edit'], []),
    (['http://osm.org'], []),
    (['https://www.openstreetmap.org/user/abc'], []),
    (['https://tile.openstreetmap.org/12/2048/2048.png'], []),
    (['Check the map at https://www.openstreetmap.org'], ['Check the map at ']),
    (['Use 203.0.113.255 for routing'], ['Use  for routing']),
    (['Find maps at https://osm.org and http://openstreetmap.org'], ['Find maps at  and ']),
    (['203.0.113.255', 'Some Address'], ['Some Address']),
    (['https://osm.org', 'Another Place'], ['Another Place']),
])
def test_split_phrases(inp, outp):
    query = [qmod.Phrase(qmod.PHRASE_ANY, text) for text in inp]

    out = run_preprocessor_on(query)
    expected_out = [qmod.Phrase(qmod.PHRASE_ANY, text) for text in outp]

    assert out == expected_out, f"Expected {expected_out}, but got {out}"
