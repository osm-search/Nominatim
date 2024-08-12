# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for executing external programs.
"""
from typing import Any, Mapping, List, Optional
import logging
import os
import re
import subprocess
import shutil

from ..typing import StrPath
from ..db.connection import get_pg_env
from ..errors import UsageError
from ..version import OSM2PGSQL_REQUIRED_VERSION

LOG = logging.getLogger()

def run_php_server(server_address: str, base_dir: StrPath) -> None:
    """ Run the built-in server from the given directory.
    """
    subprocess.run(['/usr/bin/env', 'php', '-S', server_address],
                   cwd=str(base_dir), check=True)


def run_osm2pgsql(options: Mapping[str, Any]) -> None:
    """ Run osm2pgsql with the given options.
    """
    _check_osm2pgsql_version(options['osm2pgsql'])

    env = get_pg_env(options['dsn'])

    cmd = [_find_osm2pgsql_cmd(options['osm2pgsql']),
           '--append' if options['append'] else '--create',
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

        for flavour in ('data', 'index'):
            if options['tablespaces'][f"main_{flavour}"]:
                env[f"NOMINATIM_TABLESPACE_PLACE_{flavour.upper()}"] = \
                    options['tablespaces'][f"main_{flavour}"]
    else:
        cmd.extend(('--output', 'gazetteer', '--hstore', '--latlon'))
        cmd.extend(_mk_tablespace_options('main', options))


    if options['flatnode_file']:
        cmd.extend(('--flat-nodes', options['flatnode_file']))

    cmd.extend(_mk_tablespace_options('slim', options))

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


def _mk_tablespace_options(ttype: str, options: Mapping[str, Any]) -> List[str]:
    cmds: List[str] = []
    for flavour in ('data', 'index'):
        if options['tablespaces'][f"{ttype}_{flavour}"]:
            cmds.extend((f"--tablespace-{ttype}-{flavour}",
                         options['tablespaces'][f"{ttype}_{flavour}"]))

    return cmds


def _find_osm2pgsql_cmd(cmdline: Optional[str]) -> str:
    if cmdline is not None:
        return cmdline

    in_path = shutil.which('osm2pgsql')
    if in_path is None:
        raise UsageError('osm2pgsql executable not found. Please install osm2pgsql first.')

    return str(in_path)


def _check_osm2pgsql_version(cmdline: Optional[str]) -> None:
    cmd = [_find_osm2pgsql_cmd(cmdline), '--version']

    result = subprocess.run(cmd, capture_output=True, check=True)

    if not result.stderr:
        raise UsageError("osm2pgsql does not print version information.")

    verinfo = result.stderr.decode('UTF-8')

    match = re.search(r'osm2pgsql version (\d+)\.(\d+)', verinfo)
    if match is None:
        raise UsageError(f"No version information found in output: {verinfo}")

    if (int(match[1]), int(match[2])) < OSM2PGSQL_REQUIRED_VERSION:
        raise UsageError(f"osm2pgsql is too old. Found version {match[1]}.{match[2]}. "
                         f"Need at least version {'.'.join(map(str, OSM2PGSQL_REQUIRED_VERSION))}.")
