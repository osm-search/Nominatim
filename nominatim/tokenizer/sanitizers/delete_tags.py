# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
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
from typing import Callable, List, Optional, Pattern, Tuple, Sequence
import re

from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.data.place_name import PlaceName
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

class _TagSanitizer:

    def __init__(self, config: SanitizerConfig) -> None:
        self.type = config.get('type', 'name')
        self.filter_kind = config.get_filter_kind()
        self.country_codes = config.get_string_list('country_code', [])
        self.allowed_ranks = self._set_allowed_ranks( \
                                            config.get_string_list('rank_address', ['0-30']))

        self.has_country_code = config.get('country_code', None) is not None

        suffixregexps = config.get_string_list('suffix', [r'[\s\S]*'])
        self.suffix_regexp = [re.compile(r) for r in suffixregexps]

        nameregexps = config.get_string_list('name', [r'[\s\S]*'])
        self.name_regexp = [re.compile(r) for r in nameregexps]



    def __call__(self, obj: ProcessInfo) -> None:
        tags = obj.names if self.type == 'name' else obj.address

        if (not tags or
             self.has_country_code and
              obj.place.country_code not in self.country_codes or
               not self.allowed_ranks[obj.place.rank_address]):
            return

        filtered_tags: List[PlaceName] = []

        for tag in tags:

            if (not self.filter_kind(tag.kind) or
                  not self._matches(tag.suffix, self.suffix_regexp) or
                    not self._matches(tag.name, self.name_regexp)):
                filtered_tags.append(tag)


        if self.type == 'name':
            obj.names = filtered_tags
        else:
            obj.address = filtered_tags


    def _set_allowed_ranks(self, ranks: Sequence[str]) -> Tuple[bool, ...]:
        """ Returns a tuple of 31 boolean values corresponding to the
            address ranks 0-30. Value at index 'i' is True if rank 'i'
            is present in the ranks or lies in the range of any of the
            ranks provided in the sanitizer configuration, otherwise
            the value is False.
        """
        allowed_ranks = [False] * 31

        for rank in ranks:
            intvl = [int(x) for x in rank.split('-')]

            start, end = (intvl[0], intvl[0]) if len(intvl) == 1 else (intvl[0], intvl[1])

            for i in range(start, end + 1):
                allowed_ranks[i] = True


        return tuple(allowed_ranks)


    def _matches(self, value: Optional[str], patterns: List[Pattern[str]]) -> bool:
        """ Returns True if the given value fully matches any of the regular
            expression pattern in the list. Otherwise, returns False.

            Note that if the value is None, it is taken as an empty string.
        """
        target = '' if value is None else value
        return any(r.fullmatch(target) is not None for r in patterns)



def create(config: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """ Create a function to process removal of certain tags.
    """

    return _TagSanitizer(config)
