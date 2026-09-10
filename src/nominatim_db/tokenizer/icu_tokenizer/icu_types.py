# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Type definitions for the ICU tokenizer.
"""
from dataclasses import dataclass

WORD_TYPES = (('country_names', 'C'),
              ('postcodes', 'P'),
              ('full_word', 'W'),
              ('housenumbers', 'H'))


@dataclass
class HousenumberTokenInfo:
    """ Holds the token ID and the normalized form of the houseunumber.
    """
    token: int
    housenumber: str


class TokenCache:
    """ Cache for token information to avoid repeated database queries.

        This cache is not thread-safe and needs to be instantiated per
        analyzer.
    """
    def __init__(self) -> None:
        self.names: dict[str, list[int]] = {}
        self.partials: dict[str, int] = {}
        self.fulls: dict[str, list[int]] = {}
        self.housenumbers: dict[str, HousenumberTokenInfo] = {}
