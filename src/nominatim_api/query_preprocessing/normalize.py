# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Normalize query text using the same ICU normalization rules that are
applied during import. If a phrase becomes empty because the normalization
removes all terms, then the phrase is deleted.

This preprocessor does not come with any extra information. Instead it will
use the configuration from the `normalization` section.
"""
from typing import cast

from .config import QueryConfig
from .base import QueryProcessingFunc
from ..search.query import Phrase


def create(config: QueryConfig) -> QueryProcessingFunc:
    normalizer = config.get('_normalizer')

    if not normalizer:
        return lambda p: p

    return lambda phrases: list(
        filter(lambda p: p.text,
               (Phrase(p.ptype, cast(str, normalizer.transliterate(p.text)))
                for p in phrases)))
