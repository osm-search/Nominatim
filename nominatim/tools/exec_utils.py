# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for executing external programs.
"""
from typing import Any, Mapping, IO
import logging
import os
import subprocess
import shutil
import urllib.request as urlrequest

from nominatim.typing import StrPath
from nominatim.version import NOMINATIM_VERSION
from nominatim.db.connection import get_pg_env

LOG = logging.getLogger()

def run_php_server(server_address: str, base_dir: StrPath) -> None:
    """ Run the built-in server from the given directory.
    """
    subprocess.run(['/usr/bin/env', 'php', '-S', server_address],
                   cwd=str(base_dir), check=True)


def run_osm2pgsql(options: Mapping[str, Any]) -> None:
    """ Run osm2pgsql with the given options.
    """
    env = get_pg_env(options['dsn'])

    osm2pgsql_cmd = options['osm2pgsql']
    if osm2pgsql_cmd is None:
        osm2pgsql_cmd = shutil.which('osm2pgsql')
        if osm2pgsql_cmd is None:
            raise RuntimeError('osm2pgsql executable not found. Please install osm2pgsql first.')

    cmd = [str(osm2pgsql_cmd),
           '--slim',
           '--log-progress', 'true',
           '--number-processes', '1' if options['append'] else str(options['threads']),
           '--cache', str(options['osm2pgsql_cache']),
           '--style', str(options['osm2pgsql_style'])
          ]

    if str(options['osm2pgsql_style']).endswith('.lua'):
        env['LUA_PATH'] = ';'.join((str(options['osm2pgsql_style_path'] / '?.lua'),
                                    os.environ.get('LUAPATH', ';')))
        cmd.extend(('--output', 'flex'))
    else:
        cmd.extend(('--output', 'gazetteer', '--hstore', '--latlon'))

    cmd.append('--append' if options['append'] else '--create')

    if options['flatnode_file']:
        cmd.extend(('--flat-nodes', options['flatnode_file']))

    for key, param in (('slim_data', '--tablespace-slim-data'),
                       ('slim_index', '--tablespace-slim-index'),
                       ('main_data', '--tablespace-main-data'),
                       ('main_index', '--tablespace-main-index')):
        if options['tablespaces'][key]:
            cmd.extend((param, options['tablespaces'][key]))

    if options['tablespaces']['main_data']:
        env['NOMINATIM_TABLESPACE_PLACE_DATA'] = options['tablespaces']['main_data']
    if options['tablespaces']['main_index']:
        env['NOMINATIM_TABLESPACE_PLACE_INDEX'] = options['tablespaces']['main_index']

    if options.get('disable_jit', False):
        env['PGOPTIONS'] = '-c jit=off -c max_parallel_workers_per_gather=0'

    if 'import_data' in options:
        cmd.extend(('-r', 'xml', '-'))
    elif isinstance(options['import_file'], list):
        for fname in options['import_file']:
            cmd.append(str(fname))
    else:
        cmd.append(str(options['import_file']))

    subprocess.run(cmd, cwd=options.get('cwd', '.'),
                   input=options.get('import_data'),
                   env=env, check=True)


def get_url(url: str) -> str:
    """ Get the contents from the given URL and return it as a UTF-8 string.
    """
    headers = {"User-Agent": f"Nominatim/{NOMINATIM_VERSION!s}"}

    try:
        request = urlrequest.Request(url, headers=headers)
        with urlrequest.urlopen(request) as response: # type: IO[bytes]
            return response.read().decode('utf-8')
    except Exception:
        LOG.fatal('Failed to load URL: %s', url)
        raise
