# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Abstract class definitions for tokenizers. These base classes are here
mainly for documentation purposes.
"""
from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any, Optional, Iterable
from pathlib import Path

from nominatim.config import Configuration
from nominatim.data.place_info import PlaceInfo
from nominatim.typing import Protocol

class AbstractAnalyzer(ABC):
    """ The analyzer provides the functions for analysing names and building
        the token database.

        Analyzers are instantiated on a per-thread base. Access to global data
        structures must be synchronised accordingly.
    """

    def __enter__(self) -> 'AbstractAnalyzer':
        return self


    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()


    @abstractmethod
    def close(self) -> None:
        """ Free all resources used by the analyzer.
        """


    @abstractmethod
    def get_word_token_info(self, words: List[str]) -> List[Tuple[str, str, int]]:
        """ Return token information for the given list of words.

            The function is used for testing and debugging only
            and does not need to be particularly efficient.

            Arguments:
                words: A list of words to look up the tokens for.
                       If a word starts with # it is assumed to be a full name
                       otherwise is a partial term.

            Returns:
                The function returns the list of all tuples that could be
                found for the given words. Each list entry is a tuple of
                (original word, word token, word id).
        """


    @abstractmethod
    def normalize_postcode(self, postcode: str) -> str:
        """ Convert the postcode to its standardized form.

            This function must yield exactly the same result as the SQL function
            `token_normalized_postcode()`.

            Arguments:
                postcode: The postcode to be normalized.

            Returns:
                The given postcode after normalization.
        """


    @abstractmethod
    def update_postcodes_from_db(self) -> None:
        """ Update the tokenizer's postcode tokens from the current content
            of the `location_postcode` table.
        """


    @abstractmethod
    def update_special_phrases(self,
                               phrases: Iterable[Tuple[str, str, str, str]],
                               should_replace: bool) -> None:
        """ Update the tokenizer's special phrase tokens from the given
            list of special phrases.

            Arguments:
                phrases: The new list of special phrases. Each entry is
                         a tuple of (phrase, class, type, operator).
                should_replace: If true, replace the current list of phrases.
                                When false, just add the given phrases to the
                                ones that already exist.
        """


    @abstractmethod
    def add_country_names(self, country_code: str, names: Dict[str, str]) -> None:
        """ Add the given names to the tokenizer's list of country tokens.

            Arguments:
                country_code: two-letter country code for the country the names
                              refer to.
                names: Dictionary of name type to name.
        """


    @abstractmethod
    def process_place(self, place: PlaceInfo) -> Any:
        """ Extract tokens for the given place and compute the
            information to be handed to the PL/pgSQL processor for building
            the search index.

            Arguments:
                place: Place information retrieved from the database.

            Returns:
                A JSON-serialisable structure that will be handed into
                the database via the `token_info` field.
        """



class AbstractTokenizer(ABC):
    """ The tokenizer instance is the central instance of the tokenizer in
        the system. There will only be a single instance of the tokenizer
        active at any time.
    """

    @abstractmethod
    def init_new_db(self, config: Configuration, init_db: bool = True) -> None:
        """ Set up a new tokenizer for the database.

            The function should copy all necessary data into the project
            directory or save it in the property table to make sure that
            the tokenizer remains stable over updates.

            Arguments:
              config: Read-only object with configuration options.

              init_db: When set to False, then initialisation of database
                tables should be skipped. This option is only required for
                migration purposes and can be safely ignored by custom
                tokenizers.

            TODO: can we move the init_db parameter somewhere else?
        """


    @abstractmethod
    def init_from_project(self, config: Configuration) -> None:
        """ Initialise the tokenizer from an existing database setup.

            The function should load all previously saved configuration from
            the project directory and/or the property table.

            Arguments:
              config: Read-only object with configuration options.
        """


    @abstractmethod
    def finalize_import(self, config: Configuration) -> None:
        """ This function is called at the very end of an import when all
            data has been imported and indexed. The tokenizer may create
            at this point any additional indexes and data structures needed
            during query time.

            Arguments:
              config: Read-only object with configuration options.
        """


    @abstractmethod
    def update_sql_functions(self, config: Configuration) -> None:
        """ Update the SQL part of the tokenizer. This function is called
            automatically on migrations or may be called explicitly by the
            user through the `nominatim refresh --functions` command.

            The tokenizer must only update the code of the tokenizer. The
            data structures or data itself must not be changed by this function.

            Arguments:
              config: Read-only object with configuration options.
        """


    @abstractmethod
    def check_database(self, config: Configuration) -> Optional[str]:
        """ Check that the database is set up correctly and ready for being
            queried.

            Arguments:
              config: Read-only object with configuration options.

            Returns:
              If an issue was found, return an error message with the
              description of the issue as well as hints for the user on
              how to resolve the issue. If everything is okay, return `None`.
        """


    @abstractmethod
    def update_statistics(self) -> None:
        """ Recompute any tokenizer statistics necessary for efficient lookup.
            This function is meant to be called from time to time by the user
            to improve performance. However, the tokenizer must not depend on
            it to be called in order to work.
        """


    @abstractmethod
    def update_word_tokens(self) -> None:
        """ Do house-keeping on the tokenizers internal data structures.
            Remove unused word tokens, resort data etc.
        """


    @abstractmethod
    def name_analyzer(self) -> AbstractAnalyzer:
        """ Create a new analyzer for tokenizing names and queries
            using this tokinzer. Analyzers are context managers and should
            be used accordingly:

            ```
            with tokenizer.name_analyzer() as analyzer:
                analyser.tokenize()
            ```

            When used outside the with construct, the caller must ensure to
            call the close() function before destructing the analyzer.
        """


class TokenizerModule(Protocol):
    """ Interface that must be exported by modules that implement their
        own tokenizer.
    """

    def create(self, dsn: str, data_dir: Path) -> AbstractTokenizer:
        """ Factory for new tokenizers.
        """
