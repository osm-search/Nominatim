# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Common data types and protocols for preprocessing.
"""
from typing import Callable

from ..typing import Protocol
from ..search.query import Phrase
from .config import QueryConfig

QueryProcessingFunc = Callable[[list[Phrase]], list[Phrase]]


class QueryHandler(Protocol):
    """ Protocol for query modules.
    """
    def create(self, config: QueryConfig) -> QueryProcessingFunc:
        """
        Create a function for preprocessing a query.

        Arguments:
            config: A dictionary with the additional configuration options
                    specified in the tokenizer configuration
        Return:
            The result is a callable which takes a list of phrases
            and returns the list modified by the preprocessor.
        """
        pass
