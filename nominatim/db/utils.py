"""
Helper functions for handling DB accesses.
"""
import subprocess
import logging
import gzip

from .connection import get_pg_env
from ..errors import UsageError

LOG = logging.getLogger()

def _pipe_to_proc(proc, fdesc):
    chunk = fdesc.read(2048)
    while chunk and proc.poll() is None:
        try:
            proc.stdin.write(chunk)
        except BrokenPipeError as exc:
            raise UsageError("Failed to execute SQL file.") from exc
        chunk = fdesc.read(2048)

    return len(chunk)

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

    if fname.suffix == '.gz':
        with gzip.open(str(fname), 'rb') as fdesc:
            remain = _pipe_to_proc(proc, fdesc)
    else:
        with fname.open('rb') as fdesc:
            remain = _pipe_to_proc(proc, fdesc)

    proc.stdin.close()

    ret = proc.wait()
    if ret != 0 or remain > 0:
        raise UsageError("Failed to execute SQL file.")
