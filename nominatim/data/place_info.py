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
from typing import Optional, Mapping, Any

class PlaceInfo:
    """ This data class contains all information the tokenizer can access
        about a place.
    """

    def __init__(self, info: Mapping[str, Any]) -> None:
        self._info = info


    @property
    def name(self) -> Optional[Mapping[str, str]]:
        """ A dictionary with the names of the place. Keys and values represent
            the full key and value of the corresponding OSM tag. Which tags
            are saved as names is determined by the import style.
            The property may be None if the place has no names.
        """
        return self._info.get('name')


    @property
    def address(self) -> Optional[Mapping[str, str]]:
        """ A dictionary with the address elements of the place. They key
            usually corresponds to the suffix part of the key of an OSM
            'addr:*' or 'isin:*' tag. There are also some special keys like
            `country` or `country_code` which merge OSM keys that contain
            the same information. See [Import Styles][1] for details.

            The property may be None if the place has no address information.

            [1]: ../customize/Import-Styles.md
        """
        return self._info.get('address')


    @property
    def country_code(self) -> Optional[str]:
        """ The country code of the country the place is in. Guaranteed
            to be a two-letter lower-case string. If the place is not inside
            any country, the property is set to None.
        """
        return self._info.get('country_code')


    @property
    def rank_address(self) -> int:
        """ The [rank address][1] before ant rank correction is applied.

            [1]: ../customize/Ranking.md#address-rank
        """
        return self._info.get('rank_address', 0)


    def is_a(self, key: str, value: str) -> bool:
        """ Set to True when the place's primary tag corresponds to the given
            key and value.
        """
        return self._info.get('class') == key and self._info.get('type') == value


    def is_country(self) -> bool:
        """ Set to True when the place is a valid country boundary.
        """
        return self.rank_address == 4 \
               and self.is_a('boundary', 'administrative') \
               and self.country_code is not None
