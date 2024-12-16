# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Common data types and protocols for preprocessing.
"""
from typing import List, Callable

from ..typing import Protocol
from ..search import query as qmod
from .config import QueryConfig

QueryProcessingFunc = Callable[[List[qmod.Phrase]], List[qmod.Phrase]]


class QueryHandler(Protocol):
    """ Protocol for query modules.
    """
    def create(self, config: QueryConfig) -> QueryProcessingFunc:
        """
        Create a function for sanitizing a place.
        Arguments:
            config: A dictionary with the additional configuration options
                    specified in the tokenizer configuration
            normalizer: A instance to transliterate text
        Return:
            The result is a list modified by the preprocessor.
        """
        pass
