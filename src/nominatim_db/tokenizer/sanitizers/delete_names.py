# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer which prevents certain names from getting into the search index.
It removes names which matches all selected properties.

Arguments:
    type: Define which type of names should be considered for removal:
          proper names of the object ('name') or names defining the address
          ('address'). (default: 'name')

    filter-kind: Define which 'kind' of names are affected.
                 Takes a string or list of strings where each
                 string is a regular expression. A name is considered
                 to be a candidate for removal if its 'kind' property
                 fully matches any of the given regular expressions.
                 (default: no filter)

    filter-suffix: Define the 'suffix' property of the names which should be
                   removed. Takes a string or list of strings where each
                   string is a regular expression. A tag is considered to be a
                   candidate for removal if its 'suffix' property fully
                   matches any of the given regular expressions.
                   (default: no filter)

    filter-name: Select a subset of name values to be deleted.
                 Takes a string or list of strings where each string
                 is a regular expression. A tag is considered to be a candidate
                 for removal if its name fully matches any of the given regular
                 expressions.
                 (default: no filter)

    filter-country: Define the country code of places whose names should be
                    considered for removed. Takes a string or list of strings
                    where each string is a two-letter lower-case country code.
                    (default: no filter)

    filter-rank: Define the address rank of places whose names should be
                 considered for removal. Takes a string or list of strings
                 where each string is a number or range of number or the
                 form <from>-<to>.
                 See https://nominatim.org/release-docs/latest/customize/Ranking/#address-rank
                 to learn more about address rank.
                 (default: no filter)


"""
from typing import Callable, Optional

from ...data.place_name import PlaceName, PlaceNames
from .base import ProcessInfo
from .config import SanitizerConfig
from ._derived_name_sanitizer import DerivedNameSanitizer


class _DeleteNameSanitizer(DerivedNameSanitizer):

    def __init__(self, config: SanitizerConfig) -> None:
        super().__init__(config, keep_original=False)
        self.filter_name = config.get_filter('filter-name')

    def compute_derived_names(self, name: PlaceName,
                              obj: ProcessInfo) -> Optional[PlaceNames]:
        return [] if self.filter_name(name.name) else None


def create(config: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """ Create a function to process removal of certain names.
    """

    return _DeleteNameSanitizer(config)
