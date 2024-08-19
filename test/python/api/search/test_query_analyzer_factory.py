# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for query analyzer creation.
"""
from pathlib import Path

import pytest

from nominatim_api.search.query_analyzer_factory import make_query_analyzer
from nominatim_api.search.icu_tokenizer import ICUQueryAnalyzer

@pytest.mark.asyncio
async def test_import_icu_tokenizer(table_factory, api):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('tokenizer', 'icu'),
                           ('tokenizer_import_normalisation', ':: lower();'),
                           ('tokenizer_import_transliteration', "'1' > '/1/'; 'ä' > 'ä '")))

    async with api.begin() as conn:
        ana = await make_query_analyzer(conn)

        assert isinstance(ana, ICUQueryAnalyzer)


@pytest.mark.asyncio
async def test_import_missing_property(table_factory, api):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT')

    async with api.begin() as conn:
        with pytest.raises(ValueError, match='Property.*not found'):
            await make_query_analyzer(conn)


@pytest.mark.asyncio
async def test_import_missing_module(table_factory, api):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('tokenizer', 'missing'),))

    async with api.begin() as conn:
        with pytest.raises(RuntimeError, match='Tokenizer not found'):
            await make_query_analyzer(conn)
