# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Configuration for Sanitizers.
"""
from typing import Any
from collections import UserDict


class QueryConfig(UserDict[str, Any]):
    """ The `QueryConfig` class is a read-only dictionary
        with configuration options for the preprocessor.
        In addition to the usual dictionary functions, the class provides
        accessors to standard preprocessor options that are used by many of the
        preprocessors.
    """
