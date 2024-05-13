# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Path settings for extra data used by Nominatim.
"""
from pathlib import Path

PHPLIB_DIR = None
DATA_DIR = (Path(__file__) / '..' / 'resources').resolve()
SQLLIB_DIR = (DATA_DIR / 'lib-sql')
CONFIG_DIR = (DATA_DIR / 'settings')
