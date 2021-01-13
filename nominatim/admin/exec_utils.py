"""
Helper functions for executing external programs.
"""
from pathlib import Path
import subprocess

def run_legacy_script(script, *args, nominatim_env=None):
        """ Run a Nominatim PHP script with the given arguments.
        """
        cmd = ['/usr/bin/env', 'php', '-Cq',
               nominatim_env.phplib_dir / 'admin' / script]
        cmd.extend(args)

        env = nominatim_env.config.get_os_env()
        env['NOMINATIM_DATADIR'] = str(nominatim_env.data_dir)
        env['NOMINATIM_BINDIR'] = str(nominatim_env.data_dir / 'utils')

        proc = subprocess.run(cmd, cwd=str(nominatim_env.project_dir), env=env)

        return proc.returncode

