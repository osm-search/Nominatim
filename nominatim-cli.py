#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper script for development to run nominatim from the source directory.
"""
from pathlib import Path
import sys

sys.path.insert(1, str((Path(__file__) / '..' / 'src').resolve()))

from nominatim_db import cli

exit(cli.nominatim(module_dir=None, osm2pgsql_path=None))
