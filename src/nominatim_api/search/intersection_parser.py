# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""Helpers for parsing intersection intent from free-form queries."""
from dataclasses import dataclass
from typing import List, Optional, Tuple
import re

from .query import Phrase, PHRASE_ANY

# Regex to split the first phrase into two street terms, using either
# '&' or 'and' as a separator.
_SEPARATOR = re.compile(r"\s*(?:&|\band\b)\s*", re.IGNORECASE)


@dataclass
class IntersectionQuery:
    """Parsed representation of a potential intersection query."""
    street_a: str
    street_b: str
    context: List[str]


def _split_intersection_head(head: str) -> Optional[Tuple[str, str]]:
    """Split the first phrase into the two street terms.

    The initial POC intentionally only accepts a single explicit separator.
    """
    parts = _SEPARATOR.split(head)
    if len(parts) != 2:
        return None

    street_a = parts[0].strip(" ,")
    street_b = parts[1].strip(" ,")
    if not street_a or not street_b:
        return None

    return street_a, street_b


def parse_intersection_query(phrases: List[Phrase]) -> Optional[IntersectionQuery]:
    """Try to parse phrases as an intersection query.

    Returns None when no clear intersection syntax is found.
    """
    if not phrases:
        return None

    # For the initial POC, only parse free-form search phrases.
    if any(p.ptype != PHRASE_ANY for p in phrases):
        return None

    head = phrases[0].text.strip()
    if not head:
        return None

    split = _split_intersection_head(head)
    if split is None:
        return None
    street_a, street_b = split

    context = [p.text.strip() for p in phrases[1:] if p.text.strip()]

    return IntersectionQuery(street_a=street_a, street_b=street_b, context=context)
