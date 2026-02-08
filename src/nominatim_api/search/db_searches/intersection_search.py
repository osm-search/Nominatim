# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Phase 1 intersection search object.

The lookup implementation is intentionally left as a no-op in this phase.
"""
from typing import List

from . import base
from ...connection import SearchConnection
from ...types import SearchDetails
from ... import results as nres


class IntersectionSearch(base.AbstractSearch):
    """Search object for street-intersection lookups."""

    SEARCH_PRIO = 0

    def __init__(self, penalty: float,
                 street_a: str, street_b: str, context: List[str]) -> None:
        super().__init__(penalty)
        self.street_a = street_a
        self.street_b = street_b
        self.context = context

    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        del conn, details
        return nres.SearchResults()
