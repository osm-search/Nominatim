"""
Helper functions for executing external programs.
"""
import logging
import os
import subprocess
import urllib.request as urlrequest
from urllib.parse import urlencode

from psycopg2.extensions import parse_dsn

from ..version import NOMINATIM_VERSION

LOG = logging.getLogger()

def run_legacy_script(script, *args, nominatim_env=None, throw_on_fail=False):
    """ Run a Nominatim PHP script with the given arguments.

        Returns the exit code of the script. If `throw_on_fail` is True
        then throw a `CalledProcessError` on a non-zero exit.
    """
    cmd = ['/usr/bin/env', 'php', '-Cq',
           nominatim_env.phplib_dir / 'admin' / script]
    cmd.extend([str(a) for a in args])

    env = nominatim_env.config.get_os_env()
    env['NOMINATIM_DATADIR'] = str(nominatim_env.data_dir)
    env['NOMINATIM_BINDIR'] = str(nominatim_env.data_dir / 'utils')
    env['NOMINATIM_SQLDIR'] = str(nominatim_env.sqllib_dir)
    env['NOMINATIM_DATABASE_MODULE_SRC_PATH'] = nominatim_env.module_dir
    if not env['NOMINATIM_OSM2PGSQL_BINARY']:
        env['NOMINATIM_OSM2PGSQL_BINARY'] = nominatim_env.osm2pgsql_path

    proc = subprocess.run(cmd, cwd=str(nominatim_env.project_dir), env=env,
                          check=throw_on_fail)

    return proc.returncode

def run_api_script(endpoint, project_dir, extra_env=None, phpcgi_bin=None,
                   params=None):
    """ Execute a Nominiatim API function.

        The function needs a project directory that contains the website
        directory with the scripts to be executed. The scripts will be run
        using php_cgi. Query parameters can be added as named arguments.

        Returns the exit code of the script.
    """
    log = logging.getLogger()
    webdir = str(project_dir / 'website')
    query_string = urlencode(params or {})

    env = dict(QUERY_STRING=query_string,
               SCRIPT_NAME='/{}.php'.format(endpoint),
               REQUEST_URI='/{}.php?{}'.format(endpoint, query_string),
               CONTEXT_DOCUMENT_ROOT=webdir,
               SCRIPT_FILENAME='{}/{}.php'.format(webdir, endpoint),
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

    proc = subprocess.run(cmd, cwd=str(project_dir), env=env, capture_output=True,
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


def run_php_server(server_address, base_dir):
    """ Run the built-in server from the given directory.
    """
    subprocess.run(['/usr/bin/env', 'php', '-S', server_address],
                   cwd=str(base_dir), check=True)


def run_osm2pgsql(options):
    """ Run osm2pgsql with the given options.
    """
    env = os.environ
    cmd = [options['osm2pgsql'],
           '--hstore', '--latlon', '--slim',
           '--with-forward-dependencies', 'false',
           '--log-progress', 'true',
           '--number-processes', str(options['threads']),
           '--cache', str(options['osm2pgsql_cache']),
           '--output', 'gazetteer',
           '--style', str(options['osm2pgsql_style'])
          ]
    if options['append']:
        cmd.append('--append')

    if options['flatnode_file']:
        cmd.extend(('--flat-nodes', options['flatnode_file']))

    dsn = parse_dsn(options['dsn'])
    if 'password' in dsn:
        env['PGPASSWORD'] = dsn['password']
    if 'dbname' in dsn:
        cmd.extend(('-d', dsn['dbname']))
    if 'user' in dsn:
        cmd.extend(('--username', dsn['user']))
    for param in ('host', 'port'):
        if param in dsn:
            cmd.extend(('--' + param, dsn[param]))

    cmd.append(str(options['import_file']))

    subprocess.run(cmd, cwd=options.get('cwd', '.'), env=env, check=True)


def get_url(url):
    """ Get the contents from the given URL and return it as a UTF-8 string.
    """
    headers = {"User-Agent" : "Nominatim/" + NOMINATIM_VERSION}

    try:
        with urlrequest.urlopen(urlrequest.Request(url, headers=headers)) as response:
            return response.read().decode('utf-8')
    except:
        LOG.fatal('Failed to load URL: %s', url)
        raise
