# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions to get appropriate asyncio loop factory based on platform.
"""
import sys
import asyncio
import selectors
from typing import TypeVar, Coroutine

_T = TypeVar('_T')


def asyncio_run(main: Coroutine[None, None, _T]) -> _T:
    """ Execute the coroutine with compatible loop factory and return the result.
    """
    if sys.platform == "win32":
        if sys.version_info >= (3, 12):
            def loop_factory() -> asyncio.AbstractEventLoop:
                return asyncio.SelectorEventLoop(selectors.DefaultSelector())
            return asyncio.run(main, loop_factory=loop_factory)  # type: ignore[call-arg]
        else:
            if (asyncio.get_event_loop_policy() != asyncio.WindowsSelectorEventLoopPolicy()):
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            return asyncio.run(main)
    else:
        return asyncio.run(main)
