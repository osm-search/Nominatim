# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Query preprocessing manager
"""

from ..errors import UsageError
from ..config import Configuration
from ..query_preprocessing.base import QueryProcessingFunc
from ..query_preprocessing.config import QueryConfig
from ..search.query import Phrase


class QueryPreprocessor:
    """ Manages a query preprocessing chain and runs it on incomming queries.
    """
    def __init__(self, config: Configuration) -> None:
        if config.config_file_exists('query_preprocessing.yaml'):
            rules = config.load_sub_configuration('query_preprocessing.yaml')
        else:
            rules = config.load_sub_configuration('icu_tokenizer.yaml')\
                          .get('query-preprocessing', [])

        self.preprocessors: list[QueryProcessingFunc] = []
        for func in rules:
            if 'step' not in func:
                raise UsageError("Preprocessing rule is missing the 'step' attribute.")
            if not isinstance(func['step'], str):
                raise UsageError("'step' attribute must be a simple string.")

            if func['step'] == 'normalize':
                raise UsageError("The 'normalize' preprocessing step is no longer required.\n"
                                 "Please remove the step from your configuration.")

            if func['step'] in ('config', 'base') or func['step'].startswith('_'):
                raise UsageError(f"Illegal step name '{func['step']}'.")

            module = config.load_plugin_module(
                        func['step'], 'nominatim_api.query_preprocessing')
            self.preprocessors.append(
                module.create(QueryConfig(func)))

    def run(self, phrases: list[Phrase]) -> list[Phrase]:
        """ Run the query processing chain on the given list of phrases.
        """
        for proc in self.preprocessors:
            phrases = proc(phrases)

        return phrases
