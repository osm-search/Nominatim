# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the status API call.
"""
import asyncio
import datetime as dt

import pytest

from nominatim_api.version import NOMINATIM_API_VERSION
import nominatim_api as napi


def test_status_no_extra_info(apiobj, frontend):
    api = frontend(apiobj)
    result = api.status()

    assert result.status == 0
    assert result.message == 'OK'
    assert result.software_version == NOMINATIM_API_VERSION
    assert result.database_version is None
    assert result.data_updated is None


def test_status_full(apiobj, frontend):
    import_date = dt.datetime(2022, 12, 7, 14, 14, 46, 0, tzinfo=dt.timezone.utc)
    apiobj.add_data('import_status',
                    [{'lastimportdate': import_date}])
    apiobj.add_data('properties',
                    [{'property': 'database_version', 'value': '99.5.4-2'}])

    api = frontend(apiobj)
    result = api.status()

    assert result.status == 0
    assert result.message == 'OK'
    assert result.software_version == NOMINATIM_API_VERSION
    assert result.database_version == '99.5.4-2'
    assert result.data_updated == import_date


def test_status_database_not_found(monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 'dbname=rgjdfkgjedkrgdfkngdfkg')

    api = napi.NominatimAPI()

    result = api.status()

    assert result.status == 700
    assert result.message == 'Database connection failed'
    assert result.software_version == NOMINATIM_API_VERSION
    assert result.database_version is None
    assert result.data_updated is None


@pytest.mark.asyncio
async def test_status_connection_timeout_single_pool(status_table, property_table, monkeypatch):
    monkeypatch.setenv('NOMINATIM_API_POOL_SIZE', '1')
    monkeypatch.setenv('NOMINATIM_REQUEST_TIMEOUT', '1')

    async with napi.NominatimAPIAsync() as api:
        async with api.begin():
            with pytest.raises((TimeoutError, asyncio.TimeoutError)):
                await api.status()

        await api.status()


@pytest.mark.asyncio
async def test_status_connection_timeout_multi_pool(status_table, property_table, monkeypatch):
    monkeypatch.setenv('NOMINATIM_API_POOL_SIZE', '2')
    monkeypatch.setenv('NOMINATIM_REQUEST_TIMEOUT', '1')

    async with napi.NominatimAPIAsync() as api:
        async with api.begin(), api.begin():
            with pytest.raises((TimeoutError, asyncio.TimeoutError)):
                await api.status()

        await api.status()
