# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Version information for Nominatim.
"""
from typing import Optional

from nominatim_core.version import NominatimVersion, parse_version

NOMINATIM_VERSION = NominatimVersion(4, 4, 99, 1)

POSTGRESQL_REQUIRED_VERSION = (9, 6)
POSTGIS_REQUIRED_VERSION = (2, 2)

# Cmake sets a variable @GIT_HASH@ by executing 'git --log'. It is not run
# on every execution of 'make'.
# cmake/tool-installed.tmpl is used to build the binary 'nominatim'. Inside
# there is a call to set the variable value below.
GIT_COMMIT_HASH : Optional[str] = None
