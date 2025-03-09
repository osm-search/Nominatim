# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for enhanced connection class for API functions.
"""
import pytest

import sqlalchemy as sa


@pytest.mark.asyncio
async def test_run_scalar(api, table_factory):
    table_factory('foo', definition='that TEXT', content=(('a', ),))

    async with api.begin() as conn:
        assert await conn.scalar(sa.text('SELECT * FROM foo')) == 'a'


@pytest.mark.asyncio
async def test_run_execute(api, table_factory):
    table_factory('foo', definition='that TEXT', content=(('a', ),))

    async with api.begin() as conn:
        result = await conn.execute(sa.text('SELECT * FROM foo'))
        assert result.fetchone()[0] == 'a'


@pytest.mark.asyncio
async def test_get_property_existing_cached(api, table_factory):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('dbv', '96723'), ))

    async with api.begin() as conn:
        assert await conn.get_property('dbv') == '96723'

        await conn.execute(sa.text('TRUNCATE nominatim_properties'))

        assert await conn.get_property('dbv') == '96723'


@pytest.mark.asyncio
async def test_get_property_existing_uncached(api, table_factory):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('dbv', '96723'), ))

    async with api.begin() as conn:
        assert await conn.get_property('dbv') == '96723'

        await conn.execute(sa.text("UPDATE nominatim_properties SET value = '1'"))

        assert await conn.get_property('dbv', cached=False) == '1'


@pytest.mark.asyncio
@pytest.mark.parametrize('param', ['foo', 'DB:server_version'])
async def test_get_property_missing(api, table_factory, param):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT')

    async with api.begin() as conn:
        with pytest.raises(ValueError):
            await conn.get_property(param)


@pytest.mark.asyncio
async def test_get_db_property_existing(api):
    async with api.begin() as conn:
        assert await conn.get_db_property('server_version') > 0


@pytest.mark.asyncio
async def test_get_db_property_bad_name(api):
    async with api.begin() as conn:
        with pytest.raises(ValueError):
            await conn.get_db_property('dfkgjd.rijg')
