"""
Helper functions for executing external programs.
"""
import logging
import subprocess
from urllib.parse import urlencode

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
    if not env['NOMINATIM_DATABASE_MODULE_PATH']:
        env['NOMINATIM_DATABASE_MODULE_PATH'] = nominatim_env.module_dir
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
        using php_cgi. Query parameters can be addd as named arguments.

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
        log.error(proc.stderr.decode('utf-8').replace('\\n', '\n'))
        return proc.returncode or 1

    result = proc.stdout.decode('utf-8')
    content_start = result.find('\r\n\r\n')

    print(result[content_start + 4:].replace('\\n', '\n'))

    return 0
