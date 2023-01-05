# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for executing external programs.
"""
from typing import Any, Union, Optional, Mapping, IO
from pathlib import Path
import logging
import os
import subprocess
import urllib.request as urlrequest
from urllib.parse import urlencode

from nominatim.config import Configuration
from nominatim.typing import StrPath
from nominatim.version import NOMINATIM_VERSION
from nominatim.db.connection import get_pg_env

LOG = logging.getLogger()

def run_legacy_script(script: StrPath, *args: Union[int, str],
                      config: Configuration,
                      throw_on_fail: bool = False) -> int:
    """ Run a Nominatim PHP script with the given arguments.

        Returns the exit code of the script. If `throw_on_fail` is True
        then throw a `CalledProcessError` on a non-zero exit.
    """
    cmd = ['/usr/bin/env', 'php', '-Cq',
           str(config.lib_dir.php / 'admin' / script)]
    cmd.extend([str(a) for a in args])

    env = config.get_os_env()
    env['NOMINATIM_DATADIR'] = str(config.lib_dir.data)
    env['NOMINATIM_SQLDIR'] = str(config.lib_dir.sql)
    env['NOMINATIM_CONFIGDIR'] = str(config.config_dir)
    env['NOMINATIM_DATABASE_MODULE_SRC_PATH'] = str(config.lib_dir.module)
    if not env['NOMINATIM_OSM2PGSQL_BINARY']:
        env['NOMINATIM_OSM2PGSQL_BINARY'] = str(config.lib_dir.osm2pgsql)

    proc = subprocess.run(cmd, cwd=str(config.project_dir), env=env,
                          check=throw_on_fail)

    return proc.returncode

def run_api_script(endpoint: str, project_dir: Path,
                   extra_env: Optional[Mapping[str, str]] = None,
                   phpcgi_bin: Optional[Path] = None,
                   params: Optional[Mapping[str, Any]] = None) -> int:
    """ Execute a Nominatim API function.

        The function needs a project directory that contains the website
        directory with the scripts to be executed. The scripts will be run
        using php_cgi. Query parameters can be added as named arguments.

        Returns the exit code of the script.
    """
    log = logging.getLogger()
    webdir = str(project_dir / 'website')
    query_string = urlencode(params or {})

    env = dict(QUERY_STRING=query_string,
               SCRIPT_NAME=f'/{endpoint}.php',
               REQUEST_URI=f'/{endpoint}.php?{query_string}',
               CONTEXT_DOCUMENT_ROOT=webdir,
               SCRIPT_FILENAME=f'{webdir}/{endpoint}.php',
               HTTP_HOST='localhost',
               HTTP_USER_AGENT='nominatim-tool',
               REMOTE_ADDR='0.0.0.0',
               DOCUMENT_ROOT=webdir,
               REQUEST_METHOD='GET',
               SERVER_PROTOCOL='HTTP/1.1',
               GATEWAY_INTERFACE='CGI/1.1',
               REDIRECT_STATUS='CGI')

    if extra_env:
        env.update(extra_env)

    if phpcgi_bin is None:
        cmd = ['/usr/bin/env', 'php-cgi']
    else:
        cmd = [str(phpcgi_bin)]

    proc = subprocess.run(cmd, cwd=str(project_dir), env=env,
                          stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          check=False)

    if proc.returncode != 0 or proc.stderr:
        if proc.stderr:
            log.error(proc.stderr.decode('utf-8').replace('\\n', '\n'))
        else:
            log.error(proc.stdout.decode('utf-8').replace('\\n', '\n'))
        return proc.returncode or 1

    result = proc.stdout.decode('utf-8')
    content_start = result.find('\r\n\r\n')

    print(result[content_start + 4:].replace('\\n', '\n'))

    return 0


def run_php_server(server_address: str, base_dir: StrPath) -> None:
    """ Run the built-in server from the given directory.
    """
    subprocess.run(['/usr/bin/env', 'php', '-S', server_address],
                   cwd=str(base_dir), check=True)


def run_osm2pgsql(options: Mapping[str, Any]) -> None:
    """ Run osm2pgsql with the given options.
    """
    env = get_pg_env(options['dsn'])
    cmd = [str(options['osm2pgsql']),
           '--hstore', '--latlon', '--slim',
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
        cmd.extend(('--output', 'gazetteer'))

    cmd.append('--append' if options['append'] else '--create')

    if options['flatnode_file']:
        cmd.extend(('--flat-nodes', options['flatnode_file']))

    for key, param in (('slim_data', '--tablespace-slim-data'),
                       ('slim_index', '--tablespace-slim-index'),
                       ('main_data', '--tablespace-main-data'),
                       ('main_index', '--tablespace-main-index')):
        if options['tablespaces'][key]:
            cmd.extend((param, options['tablespaces'][key]))

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
