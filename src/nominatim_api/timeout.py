# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helpers for handling of timeouts for request.
"""
from typing import Union, Optional
import asyncio


class Timeout:
    """ A class that provides helper functions to ensure a given timeout
        is respected. Can only be used from coroutines.
    """
    def __init__(self, timeout: Optional[Union[int, float]]) -> None:
        self.abs = None if timeout is None else asyncio.get_running_loop().time() + timeout

    def is_elapsed(self) -> bool:
        """ Check if the timeout has already passed.
        """
        return (self.abs is not None) and (asyncio.get_running_loop().time() >= self.abs)
