# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of API version v1 (aka the legacy version).
"""

#pylint: disable=useless-import-alias

from .server_glue import (ASGIAdaptor as ASGIAdaptor,
                          EndpointFunc as EndpointFunc,
                          ROUTES as ROUTES)

from . import format as _format

list_formats = _format.dispatch.list_formats
supports_format = _format.dispatch.supports_format
format_result = _format.dispatch.format_result
