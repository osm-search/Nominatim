# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Path settings for extra data used by Nominatim.
"""
from pathlib import Path

PHPLIB_DIR = (Path(__file__) / '..' / '..' / 'lib-php').resolve()
SQLLIB_DIR = (Path(__file__) / '..' / '..' / 'lib-sql').resolve()
DATA_DIR = (Path(__file__) / '..' / '..' / 'data').resolve()
CONFIG_DIR = (Path(__file__) / '..' / '..' / 'settings').resolve()
