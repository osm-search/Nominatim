# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Implementation of the acutal database accesses for forward search.
"""
import abc

from nominatim.api.connection import SearchConnection
from nominatim.api.types import SearchDetails
import nominatim.api.results as nres
from nominatim.api.search.db_search_fields import SearchData, WeightedCategories

class AbstractSearch(abc.ABC):
    """ Encapuslation of a single lookup in the database.
    """

    def __init__(self, penalty: float) -> None:
        self.penalty = penalty

    @abc.abstractmethod
    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """


class NearSearch(AbstractSearch):
    """ Category search of a place type near the result of another search.
    """
    def __init__(self, penalty: float, categories: WeightedCategories,
                 search: AbstractSearch) -> None:
        super().__init__(penalty)
        self.search = search
        self.categories = categories


    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        return nres.SearchResults([])


class PoiSearch(AbstractSearch):
    """ Category search in a geographic area.
    """
    def __init__(self, sdata: SearchData) -> None:
        super().__init__(sdata.penalty)
        self.categories = sdata.qualifiers
        self.countries = sdata.countries


    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        return nres.SearchResults([])


class CountrySearch(AbstractSearch):
    """ Search for a country name or country code.
    """
    def __init__(self, sdata: SearchData) -> None:
        super().__init__(sdata.penalty)
        self.countries = sdata.countries


    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        return nres.SearchResults([])


class PostcodeSearch(AbstractSearch):
    """ Search for a postcode.
    """
    def __init__(self, extra_penalty: float, sdata: SearchData) -> None:
        super().__init__(sdata.penalty + extra_penalty)
        self.countries = sdata.countries
        self.postcodes = sdata.postcodes
        self.lookups = sdata.lookups
        self.rankings = sdata.rankings


    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        return nres.SearchResults([])


class PlaceSearch(AbstractSearch):
    """ Generic search for an address or named place.
    """
    def __init__(self, extra_penalty: float, sdata: SearchData, expected_count: int) -> None:
        super().__init__(sdata.penalty + extra_penalty)
        self.countries = sdata.countries
        self.postcodes = sdata.postcodes
        self.housenumbers = sdata.housenumbers
        self.qualifiers = sdata.qualifiers
        self.lookups = sdata.lookups
        self.rankings = sdata.rankings
        self.expected_count = expected_count


    async def lookup(self, conn: SearchConnection,
                     details: SearchDetails) -> nres.SearchResults:
        """ Find results for the search in the database.
        """
        return nres.SearchResults([])
