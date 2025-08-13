# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Module for localization
"""
from .simple import (SimpleLocales as SimpleLocales)
from .complex import (ComplexLocales as ComplexLocales, load_lang_info as load_lang_info)
