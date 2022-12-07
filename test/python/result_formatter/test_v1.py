# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for formatting results for the V1 API.
"""
import datetime as dt
import pytest

import nominatim.result_formatter.v1 as format_module
from nominatim.apicmd.status import StatusResult
from nominatim.version import version_str

STATUS_FORMATS = {'text', 'json'}

class TestStatusResultFormat:


    @pytest.fixture(autouse=True)
    def make_formatter(self):
        self.formatter = format_module.create(StatusResult)


    def test_format_list(self):
        assert set(self.formatter.list_formats()) == STATUS_FORMATS


    @pytest.mark.parametrize('fmt', list(STATUS_FORMATS))
    def test_supported(self, fmt):
        assert self.formatter.supports_format(fmt)


    def test_unsupported(self):
        assert not self.formatter.supports_format('gagaga')


    def test_format_text(self):
        assert self.formatter.format(StatusResult(0, 'message here'), 'text') == 'OK'


    def test_format_text(self):
        assert self.formatter.format(StatusResult(500, 'message here'), 'text') == 'ERROR: message here'


    def test_format_json_minimal(self):
        status = StatusResult(700, 'Bad format.')

        result = self.formatter.format(status, 'json')

        assert result == '{"status": 700, "message": "Bad format.", "software_version": "%s"}' % (version_str())


    def test_format_json_full(self):
        status = StatusResult(0, 'OK')
        status.data_updated = dt.datetime(2010, 2, 7, 20, 20, 3, 0, tzinfo=dt.timezone.utc)
        status.database_version = '5.6'

        result = self.formatter.format(status, 'json')

        assert result == '{"status": 0, "message": "OK", "data_updated": "2010-02-07T20:20:03+00:00", "software_version": "%s", "database_version": "5.6"}' % (version_str())
