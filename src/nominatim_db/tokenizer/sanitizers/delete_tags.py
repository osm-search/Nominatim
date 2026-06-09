# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
DEPRECATED, use delete-names instead.

Sanitizer which prevents certain tags from getting into the search index.
It remove tags which matches all properties given below.


Arguments:
    type: Define which type of tags should be considered for removal.
          There are two types of tags 'name' and 'address' tags.
          Takes a string 'name' or 'address'. (default: 'name')

    filter-kind: Define which 'kind' of tags should be removed.
                 Takes a string or list of strings where each
                 string is a regular expression. A tag is considered
                 to be a candidate for removal if its 'kind' property
                 fully matches any of the given regular expressions.
                 Note that by default all 'kind' of tags are considered.

    suffix: Define the 'suffix' property of the tags which should be
            removed. Takes a string or list of strings where each
            string is a regular expression. A tag is considered to be a
            candidate for removal if its 'suffix' property fully
            matches any of the given regular expressions. Note that by
            default tags with any suffix value are considered including
            those which don't have a suffix at all.

    name: Define the 'name' property corresponding to the 'kind' property
          of the tag. Takes a string or list of strings where each string
          is a regular expression. A tag is considered to be a candidate
          for removal if its name fully matches any of the given regular
          expressions. Note that by default tags with any 'name' are
          considered.

    country_code: Define the country code of places whose tags should be
                  considered for removed. Takes a string or list of strings
                  where each string is a two-letter lower-case country code.
                  Note that by default tags of places with any country code
                  are considered including those which don't have a country
                  code at all.

    rank_address: Define the address rank of places whose tags should be
                  considered for removal. Takes a string or list of strings
                  where each string is a number or range of number or the
                  form <from>-<to>.
                  Note that default is '0-30', which means that tags of all
                  places are considered.
                  See https://nominatim.org/release-docs/latest/customize/Ranking/#address-rank
                  to learn more about address rank.


"""
from typing import Optional

from ...data.place_name import PlaceName, PlaceNames
from .base import ProcessInfo, SanitizerFunc
from .config import SanitizerConfig
from ._derived_name_sanitizer import DerivedNameSanitizer


class _DeleteNameSanitizer(DerivedNameSanitizer):

    def __init__(self, config: SanitizerConfig) -> None:
        super().__init__(config, keep_original=False,
                         filter_country_option='country_code',
                         filter_suffix_option='suffix',
                         filter_rank_option='rank_address')
        self.filter_name = config.get_filter('name')

    def compute_derived_names(self, name: PlaceName,
                              obj: ProcessInfo) -> Optional[PlaceNames]:
        return [] if self.filter_name(name.name) else None


def create(config: SanitizerConfig) -> SanitizerFunc:
    """ Create a function to process removal of certain tags.
    """

    return _DeleteNameSanitizer(config)
