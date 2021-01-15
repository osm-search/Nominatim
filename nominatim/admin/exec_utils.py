"""
Helper functions for executing external programs.
"""
import subprocess

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
