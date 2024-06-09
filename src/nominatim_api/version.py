# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Version information for the Nominatim API.
"""

# See also https://github.com/PyCQA/pylint/issues/6006
# pylint: disable=useless-import-alias,unused-import

from nominatim_core.version import (NominatimVersion as NominatimVersion,
                                    parse_version as parse_version)

NOMINATIM_API_VERSION = '4.4.99'
