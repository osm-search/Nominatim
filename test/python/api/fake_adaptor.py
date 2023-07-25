# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Provides dummy implementations of ASGIAdaptor for testing.
"""
from collections import namedtuple

import nominatim.api.v1.server_glue as glue
from nominatim.config import Configuration

class FakeError(BaseException):

    def __init__(self, msg, status):
        self.msg = msg
        self.status = status

    def __str__(self):
        return f'{self.status} -- {self.msg}'

FakeResponse = namedtuple('FakeResponse', ['status', 'output', 'content_type'])

class FakeAdaptor(glue.ASGIAdaptor):

    def __init__(self, params=None, headers=None, config=None):
        self.params = params or {}
        self.headers = headers or {}
        self._config = config or Configuration(None)


    def get(self, name, default=None):
        return self.params.get(name, default)


    def get_header(self, name, default=None):
        return self.headers.get(name, default)


    def error(self, msg, status=400):
        return FakeError(msg, status)


    def create_response(self, status, output):
        return FakeResponse(status, output, self.content_type)


    def config(self):
        return self._config

