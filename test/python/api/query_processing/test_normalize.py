# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for normalizing search queries.
"""
from pathlib import Path

import pytest

from icu import Transliterator

import nominatim_api.search.query as qmod
from nominatim_api.query_preprocessing.config import QueryConfig
from nominatim_api.query_preprocessing import normalize

def run_preprocessor_on(query, norm):
    normalizer = Transliterator.createFromRules("normalization", norm)
    proc = normalize.create(QueryConfig().set_normalizer(normalizer))

    return proc(query)


def test_normalize_simple():
    norm = ':: lower();'
    query = [qmod.Phrase(qmod.PhraseType.NONE, 'Hallo')]

    out = run_preprocessor_on(query, norm)

    assert len(out) == 1
    assert out == [qmod.Phrase(qmod.PhraseType.NONE, 'hallo')]
