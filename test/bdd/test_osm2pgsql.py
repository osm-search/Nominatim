# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Collector for BDD osm2pgsql import style tests.
"""
import asyncio
import random

import pytest
from pytest_bdd import scenarios, when, given

from nominatim_db import cli
from nominatim_db.tools.exec_utils import run_osm2pgsql
from nominatim_db.tools.database_import import load_data, create_table_triggers
from nominatim_db.tools.replication import run_osm2pgsql_updates


@pytest.fixture
def osm2pgsql_options(def_config):
    return dict(osm2pgsql='osm2pgsql',
                osm2pgsql_cache=50,
                osm2pgsql_style=str(def_config.get_import_style_file()),
                osm2pgsql_style_path=def_config.lib_dir.lua,
                threads=1,
                dsn=def_config.get_libpq_dsn(),
                flatnode_file='',
                tablespaces=dict(slim_data='', slim_index='',
                                 main_data='', main_index=''),
                append=False)


@pytest.fixture
def opl_writer(tmp_path, node_grid):
    nr = [0]

    def _write(data):
        fname = tmp_path / f"test_osm_{nr[0]}.opl"
        nr[0] += 1
        with fname.open('wt') as fd:
            for line in data.split('\n'):
                if line.startswith('n') and ' x' not in line:
                    coord = node_grid.get(line[1:].split(' ')[0]) \
                            or (random.uniform(-180, 180), random.uniform(-90, 90))
                    line = f"{line} x{coord[0]:.7f} y{coord[1]:.7f}"
                fd.write(line)
                fd.write('\n')
        return fname

    return _write


@given('the lua style file', target_fixture='osm2pgsql_options')
def set_lua_style_file(osm2pgsql_options, docstring, tmp_path):
    style = tmp_path / 'custom.lua'
    style.write_text(docstring)
    osm2pgsql_options['osm2pgsql_style'] = str(style)

    return osm2pgsql_options


@when('loading osm data')
def load_from_osm_file(db, osm2pgsql_options, opl_writer, docstring):
    """ Load the given data into a freshly created test database using osm2pgsql.
        No further indexing is done.

        The data is expected as attached text in OPL format.
    """
    osm2pgsql_options['import_file'] = opl_writer(docstring.replace(r'//', r'/'))
    osm2pgsql_options['append'] = False
    run_osm2pgsql(osm2pgsql_options)


@when('updating osm data')
def update_from_osm_file(db_conn, def_config, osm2pgsql_options, opl_writer, docstring):
    """ Update a database previously populated with 'loading osm data'.
        Needs to run indexing on the existing data first to yield the correct
        result.

        The data is expected as attached text in OPL format.
    """
    create_table_triggers(db_conn, def_config)
    asyncio.run(load_data(def_config.get_libpq_dsn(), 1))
    cli.nominatim(['index'], def_config.environ)
    cli.nominatim(['refresh', '--functions'], def_config.environ)

    osm2pgsql_options['import_file'] = opl_writer(docstring.replace(r'//', r'/'))
    run_osm2pgsql_updates(db_conn, osm2pgsql_options)


scenarios('features/osm2pgsql')
