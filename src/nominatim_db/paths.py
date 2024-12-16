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

SQLLIB_DIR = (Path(__file__) / '..' / '..' / '..' / 'lib-sql').resolve()
LUALIB_DIR = (Path(__file__) / '..' / '..' / '..' / 'lib-lua').resolve()
DATA_DIR = (Path(__file__) / '..' / '..' / '..' / 'data').resolve()
CONFIG_DIR = (Path(__file__) / '..' / '..' / '..' / 'settings').resolve()
