# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for handling DB accesses.
"""
from typing import IO, Optional, Union
import subprocess
import logging
import gzip
from pathlib import Path

from .connection import get_pg_env
from ..errors import UsageError

LOG = logging.getLogger()

def _pipe_to_proc(proc: 'subprocess.Popen[bytes]',
                  fdesc: Union[IO[bytes], gzip.GzipFile]) -> int:
    assert proc.stdin is not None
    chunk = fdesc.read(2048)
    while chunk and proc.poll() is None:
        try:
            proc.stdin.write(chunk)
        except BrokenPipeError as exc:
            raise UsageError("Failed to execute SQL file.") from exc
        chunk = fdesc.read(2048)

    return len(chunk)

def execute_file(dsn: str, fname: Path,
                 ignore_errors: bool = False,
                 pre_code: Optional[str] = None,
                 post_code: Optional[str] = None) -> None:
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

    with subprocess.Popen(cmd, env=get_pg_env(dsn), stdin=subprocess.PIPE) as proc:
        assert proc.stdin is not None
        try:
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
        finally:
            proc.stdin.close()
            ret = proc.wait()

    if ret != 0 or remain > 0:
        raise UsageError("Failed to execute SQL file.")
