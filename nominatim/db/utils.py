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

def execute_file(dsn, fname, ignore_errors=False, pre_code=None, post_code=None):
    """ Read an SQL file and run its contents against the given database
        using psql. Use `pre_code` and `post_code` to run extra commands
        before or after executing the file. The commands are run within the
        same session, so they may be used to wrap the file execution in a
        transaction.
    """
    cmd = ['psql']
    if not ignore_errors:
        cmd.extend(('-v', 'ON_ERROR_STOP=1'))
    if not LOG.isEnabledFor(logging.INFO):
        cmd.append('--quiet')
    proc = subprocess.Popen(cmd, env=get_pg_env(dsn), stdin=subprocess.PIPE)

    if not LOG.isEnabledFor(logging.INFO):
        proc.stdin.write('set client_min_messages to WARNING;'.encode('utf-8'))

    if pre_code:
        proc.stdin.write((pre_code + ';').encode('utf-8'))

    if fname.suffix == '.gz':
        with gzip.open(str(fname), 'rb') as fdesc:
            remain = _pipe_to_proc(proc, fdesc)
    else:
        with fname.open('rb') as fdesc:
            remain = _pipe_to_proc(proc, fdesc)

    if remain == 0 and post_code:
        proc.stdin.write((';' + post_code).encode('utf-8'))

    proc.stdin.close()

    ret = proc.wait()
    if ret != 0 or remain > 0:
        raise UsageError("Failed to execute SQL file.")
