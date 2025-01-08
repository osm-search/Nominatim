# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for japanese phrase splitting.
"""
from pathlib import Path

import pytest

from icu import Transliterator

import nominatim_api.search.query as qmod
from nominatim_api.query_preprocessing.config import QueryConfig
from nominatim_api.query_preprocessing import split_japanese_phrases

def run_preprocessor_on(query):
    proc = split_japanese_phrases.create(QueryConfig().set_normalizer(None))

    return proc(query)


@pytest.mark.parametrize('inp,outp', [('大阪府大阪市大阪', '大阪府:大阪市:大阪'),
                                      ('大阪府大阪', '大阪府:大阪'),
                                      ('大阪市大阪', '大阪市:大阪')])
def test_split_phrases(inp, outp):
    query = [qmod.Phrase(qmod.PhraseType.NONE, inp)]

    out = run_preprocessor_on(query)

    assert out == [qmod.Phrase(qmod.PhraseType.NONE, outp)]
