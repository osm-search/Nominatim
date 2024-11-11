# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for accessing URL.
"""
from typing import IO  # noqa
import logging
import urllib.request as urlrequest

from ..version import NOMINATIM_VERSION

LOG = logging.getLogger()


def get_url(url: str) -> str:
    """ Get the contents from the given URL and return it as a UTF-8 string.

        This version makes sure that an appropriate user agent is sent.
    """
    headers = {"User-Agent": f"Nominatim/{NOMINATIM_VERSION!s}"}

    try:
        request = urlrequest.Request(url, headers=headers)
        with urlrequest.urlopen(request) as response:  # type: IO[bytes]
            return response.read().decode('utf-8')
    except Exception:
        LOG.fatal('Failed to load URL: %s', url)
        raise
