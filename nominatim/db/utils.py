"""
Helper functions for handling DB accesses.
"""
import subprocess
import logging

from .connection import get_pg_env
from ..errors import UsageError

LOG = logging.getLogger()

def execute_file(dsn, fname, ignore_errors=False):
    """ Read an SQL file and run its contents against the given database
        using psql.
    """
    cmd = ['psql']
    if not ignore_errors:
        cmd.extend(('-v', 'ON_ERROR_STOP=1'))
    proc = subprocess.Popen(cmd, env=get_pg_env(dsn), stdin=subprocess.PIPE)

    if not LOG.isEnabledFor(logging.INFO):
        proc.stdin.write('set client_min_messages to WARNING;'.encode('utf-8'))

    with fname.open('rb') as fdesc:
        chunk = fdesc.read(2048)
        while chunk and proc.poll() is None:
            proc.stdin.write(chunk)
            chunk = fdesc.read(2048)

    proc.stdin.close()

    ret = proc.wait()
    print(ret, chunk)
    if ret != 0 or chunk:
        raise UsageError("Failed to execute SQL file.")
