# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Various smaller helps for step execution.
"""
import logging
import subprocess

LOG = logging.getLogger(__name__)

def run_script(cmd, **kwargs):
    """ Run the given command, check that it is successful and output
        when necessary.
    """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            **kwargs)
    (outp, outerr) = proc.communicate()
    outp = outp.decode('utf-8')
    outerr = outerr.decode('utf-8').replace('\\n', '\n')
    LOG.debug("Run command: %s\n%s\n%s", cmd, outp, outerr)

    assert proc.returncode == 0, "Script '{}' failed:\n{}\n{}\n".format(cmd[0], outp, outerr)

    return outp, outerr
