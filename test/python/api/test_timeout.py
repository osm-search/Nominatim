# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for timeout helper
"""
import asyncio

import pytest

from nominatim_api.timeout import Timeout


@pytest.mark.asyncio
async def test_timeout_none():
    timeout = Timeout(None)

    assert timeout.abs is None
    assert not timeout.is_elapsed()


@pytest.mark.asyncio
async def test_timeout_should_not_be_elapsed_after_creation():
    assert not Timeout(2).is_elapsed()


@pytest.mark.asyncio
async def test_timeout_elapse():
    timeout = Timeout(0.5)

    assert timeout.abs is not None
    await asyncio.sleep(0.5)
    assert timeout.is_elapsed()
