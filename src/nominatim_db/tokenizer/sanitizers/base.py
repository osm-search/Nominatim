# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Common data types and protocols for sanitizers.
"""
from typing import Optional, List, Mapping, Callable

from nominatim_core.typing import Protocol, Final
from ...data.place_info import PlaceInfo
from ...data.place_name import PlaceName
from .config import SanitizerConfig


class ProcessInfo:
    """ Container class for information handed into to handler functions.
        The 'names' and 'address' members are mutable. A handler must change
        them by either modifying the lists place or replacing the old content
        with a new list.
    """

    def __init__(self, place: PlaceInfo):
        self.place: Final = place
        self.names = self._convert_name_dict(place.name)
        self.address = self._convert_name_dict(place.address)


    @staticmethod
    def _convert_name_dict(names: Optional[Mapping[str, str]]) -> List[PlaceName]:
        """ Convert a dictionary of names into a list of PlaceNames.
            The dictionary key is split into the primary part of the key
            and the suffix (the part after an optional colon).
        """
        out = []

        if names:
            for key, value in names.items():
                parts = key.split(':', 1)
                out.append(PlaceName(value.strip(),
                                     parts[0].strip(),
                                     parts[1].strip() if len(parts) > 1 else None))

        return out


class SanitizerHandler(Protocol):
    """ Protocol for sanitizer modules.
    """

    def create(self, config: SanitizerConfig) -> Callable[[ProcessInfo], None]:
        """
        Create a function for sanitizing a place.

        Arguments:
            config: A dictionary with the additional configuration options
                    specified in the tokenizer configuration

        Return:
            The result must be a callable that takes a place description
            and transforms name and address as required.
        """
