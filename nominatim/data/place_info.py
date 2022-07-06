# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Wrapper around place information the indexer gets from the database and hands to
the tokenizer.
"""

import psycopg2.extras

class PlaceInfo:
    """ Data class containing all information the tokenizer gets about a
        place it should process the names for.
    """

    def __init__(self, info):
        self._info = info


    def analyze(self, analyzer):
        """ Process this place with the given tokenizer and return the
            result in psycopg2-compatible Json.
        """
        return psycopg2.extras.Json(analyzer.process_place(self))


    @property
    def name(self):
        """ A dictionary with the names of the place or None if the place
            has no names.
        """
        return self._info.get('name')


    @property
    def address(self):
        """ A dictionary with the address elements of the place
            or None if no address information is available.
        """
        return self._info.get('address')


    @property
    def country_code(self):
        """ The country code of the country the place is in. Guaranteed
            to be a two-letter lower-case string or None, if no country
            could be found.
        """
        return self._info.get('country_code')


    @property
    def rank_address(self):
        """ The computed rank address before rank correction.
        """
        return self._info.get('rank_address')


    def is_a(self, key, value):
        """ Check if the place's primary tag corresponds to the given
            key and value.
        """
        return self._info.get('class') == key and self._info.get('type') == value


    def is_country(self):
        """ Check if the place is a valid country boundary.
        """
        return self.rank_address == 4 \
               and self.is_a('boundary', 'administrative') \
               and self.country_code is not None
