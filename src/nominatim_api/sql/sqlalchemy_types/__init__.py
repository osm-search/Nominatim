# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Module with custom types for SQLAlchemy
"""

# See also https://github.com/PyCQA/pylint/issues/6006
# pylint: disable=useless-import-alias

from .geometry import (Geometry as Geometry)
from .int_array import (IntArray as IntArray)
from .key_value import (KeyValueStore as KeyValueStore)
from .json import (Json as Json)
