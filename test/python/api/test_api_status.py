# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for the status API call.
"""
from pathlib import Path
import datetime as dt
import pytest

from nominatim.version import version_str
from nominatim.api import NominatimAPI

def test_status_no_extra_info(apiobj, table_factory):
    table_factory('import_status',
                  definition="lastimportdate timestamp with time zone NOT NULL")
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT')

    result = apiobj.status()

    assert result.status == 0
    assert result.message == 'OK'
    assert result.software_version == version_str()
    assert result.database_version is None
    assert result.data_updated is None


def test_status_full(apiobj, table_factory):
    table_factory('import_status',
                  definition="lastimportdate timestamp with time zone NOT NULL",
                  content=(('2022-12-07 15:14:46+01',),))
    table_factory('nominatim_properties',
                  definition='property TEXT, value TEXT',
                  content=(('database_version', '99.5.4-2'), ))

    result = apiobj.status()

    assert result.status == 0
    assert result.message == 'OK'
    assert result.software_version == version_str()
    assert result.database_version == '99.5.4-2'
    assert result.data_updated == dt.datetime(2022, 12, 7, 14, 14, 46, 0, tzinfo=dt.timezone.utc)


def test_status_database_not_found(monkeypatch):
    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 'dbname=rgjdfkgjedkrgdfkngdfkg')

    api = NominatimAPI(Path('/invalid'), {})

    result = api.status()

    assert result.status == 700
    assert result.message == 'Database connection failed'
    assert result.software_version == version_str()
    assert result.database_version is None
    assert result.data_updated is None
