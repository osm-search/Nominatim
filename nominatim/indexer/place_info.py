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
    def country_feature(self):
        """ Return the country code if the place is a valid country boundary.
        """
        return self._info.get('country_feature')
