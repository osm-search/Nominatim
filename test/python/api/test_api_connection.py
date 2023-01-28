# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for enhanced connection class for API functions.
"""
from pathlib import Path
import pytest
import pytest_asyncio

import sqlalchemy as sa

from nominatim.api import NominatimAPIAsync

@pytest_asyncio.fixture
async def apiobj(temp_db):
    """ Create an asynchronous SQLAlchemy engine for the test DB.
    """
    api = NominatimAPIAsync(Path('/invalid'), {})
    yield api
    await api.close()


@pytest.mark.asyncio
async def test_run_scalar(apiobj, table_factory):
    table_factory('foo', definition='that TEXT', content=(('a', ),))

    async with apiobj.begin() as conn:
        assert await conn.scalar(sa.text('SELECT * FROM foo')) == 'a'


@pytest.mark.asyncio
async def test_run_execute(apiobj, table_factory):
    table_factory('foo', definition='that TEXT', content=(('a', ),))

    async with apiobj.begin() as conn:
        result = await conn.execute(sa.text('SELECT * FROM foo'))
        assert result.fetchone()[0] == 'a'


@pytest.mark.asyncio
async def test_get_property_existing_cached(apiobj, table_factory):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('dbv', '96723'), ))

    async with apiobj.begin() as conn:
        assert await conn.get_property('dbv') == '96723'

        await conn.execute(sa.text('TRUNCATE nominatim_properties'))

        assert await conn.get_property('dbv') == '96723'


@pytest.mark.asyncio
async def test_get_property_existing_uncached(apiobj, table_factory):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('dbv', '96723'), ))

    async with apiobj.begin() as conn:
        assert await conn.get_property('dbv') == '96723'

        await conn.execute(sa.text("UPDATE nominatim_properties SET value = '1'"))

        assert await conn.get_property('dbv', cached=False) == '1'


@pytest.mark.asyncio
@pytest.mark.parametrize('param', ['foo', 'DB:server_version'])
async def test_get_property_missing(apiobj, table_factory, param):
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT')

    async with apiobj.begin() as conn:
        with pytest.raises(ValueError):
            await conn.get_property(param)


@pytest.mark.asyncio
async def test_get_db_property_existing(apiobj):
    async with apiobj.begin() as conn:
        assert await conn.get_db_property('server_version') > 0


@pytest.mark.asyncio
async def test_get_db_property_existing(apiobj):
    async with apiobj.begin() as conn:
        with pytest.raises(ValueError):
            await conn.get_db_property('dfkgjd.rijg')
