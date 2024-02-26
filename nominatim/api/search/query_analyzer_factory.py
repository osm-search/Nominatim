# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Factory for creating a query analyzer for the configured tokenizer.
"""
from typing import List, cast, TYPE_CHECKING
from abc import ABC, abstractmethod
from pathlib import Path
import importlib

from nominatim.api.logging import log
from nominatim.api.connection import SearchConnection

if TYPE_CHECKING:
    from nominatim.api.search.query import Phrase, QueryStruct

class AbstractQueryAnalyzer(ABC):
    """ Class for analysing incoming queries.

        Query analyzers are tied to the tokenizer used on import.
    """

    @abstractmethod
    async def analyze_query(self, phrases: List['Phrase']) -> 'QueryStruct':
        """ Analyze the given phrases and return the tokenized query.
        """


    @abstractmethod
    def normalize_text(self, text: str) -> str:
        """ Bring the given text into a normalized form. That is the
            standardized form search will work with. All information removed
            at this stage is inevitably lost.
        """



async def make_query_analyzer(conn: SearchConnection) -> AbstractQueryAnalyzer:
    """ Create a query analyzer for the tokenizer used by the database.
    """
    name = await conn.get_property('tokenizer')

    src_file = Path(__file__).parent / f'{name}_tokenizer.py'
    if not src_file.is_file():
        log().comment(f"No tokenizer named '{name}' available. Database not set up properly.")
        raise RuntimeError('Tokenizer not found')

    module = importlib.import_module(f'nominatim.api.search.{name}_tokenizer')

    return cast(AbstractQueryAnalyzer, await module.create_query_analyzer(conn))
