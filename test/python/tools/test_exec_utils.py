# SPDX-FileCopyrightText: 2023 Nominatim developer community <https://nominatim.org>
#
# SPDX-License-Identifier: GPL-2.0-only

# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for tools.exec_utils module.
"""
from pathlib import Path
import subprocess

import pytest

from nominatim.config import Configuration
import nominatim.tools.exec_utils as exec_utils
import nominatim.paths


### run_osm2pgsql

def test_run_osm2pgsql(osm2pgsql_options):
    osm2pgsql_options['append'] = False
    osm2pgsql_options['import_file'] = 'foo.bar'
    osm2pgsql_options['tablespaces']['slim_data'] = 'extra'
    exec_utils.run_osm2pgsql(osm2pgsql_options)


def test_run_osm2pgsql_disable_jit(osm2pgsql_options):
    osm2pgsql_options['append'] = True
    osm2pgsql_options['import_file'] = 'foo.bar'
    osm2pgsql_options['disable_jit'] = True
    exec_utils.run_osm2pgsql(osm2pgsql_options)
