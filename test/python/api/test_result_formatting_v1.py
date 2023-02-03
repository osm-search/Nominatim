# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for formatting results for the V1 API.
"""
import datetime as dt
import pytest

import nominatim.api.v1 as api_impl
from nominatim.api import StatusResult
from nominatim.version import NOMINATIM_VERSION

STATUS_FORMATS = {'text', 'json'}

# StatusResult

def test_status_format_list():
    assert set(api_impl.list_formats(StatusResult)) == STATUS_FORMATS


@pytest.mark.parametrize('fmt', list(STATUS_FORMATS))
def test_status_supported(fmt):
    assert api_impl.supports_format(StatusResult, fmt)


def test_status_unsupported():
    assert not api_impl.supports_format(StatusResult, 'gagaga')


def test_status_format_text():
    assert api_impl.format_result(StatusResult(0, 'message here'), 'text', {}) == 'OK'


def test_status_format_text():
    assert api_impl.format_result(StatusResult(500, 'message here'), 'text', {}) == 'ERROR: message here'


def test_status_format_json_minimal():
    status = StatusResult(700, 'Bad format.')

    result = api_impl.format_result(status, 'json', {})

    assert result == '{"status":700,"message":"Bad format.","software_version":"%s"}' % (NOMINATIM_VERSION, )


def test_status_format_json_full():
    status = StatusResult(0, 'OK')
    status.data_updated = dt.datetime(2010, 2, 7, 20, 20, 3, 0, tzinfo=dt.timezone.utc)
    status.database_version = '5.6'

    result = api_impl.format_result(status, 'json', {})

    assert result == '{"status":0,"message":"OK","data_updated":"2010-02-07T20:20:03+00:00","software_version":"%s","database_version":"5.6"}' % (NOMINATIM_VERSION, )
