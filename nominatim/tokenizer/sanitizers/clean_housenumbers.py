# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer that preprocesses address tags for house numbers. The sanitizer
allows to

* define which tags are to be considered house numbers (see 'filter-kind')
* split house number lists into individual numbers (see 'delimiters')

Arguments:
    delimiters: Define the set of characters to be used for
                splitting a list of house numbers into parts. (default: ',;')
    filter-kind: Define the address tags that are considered to be a
                 house number. Either takes a single string or a list of strings,
                 where each string is a regular expression. An address item
                 is considered a house number if the 'kind' fully matches any
                 of the given regular expressions. (default: 'housenumber')
    convert-to-name: Define house numbers that should be treated as a name
                     instead of a house number. Either takes a single string
                     or a list of strings, where each string is a regular
                     expression that must match the full house number value.
"""
from typing import Callable, Iterator, List
import re

from nominatim.tokenizer.sanitizers.base import ProcessInfo, PlaceName
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

class _HousenumberSanitizer:

    def __init__(self, config: SanitizerConfig) -> None:
        self.filter_kind = config.get_filter_kind('housenumber')
        self.split_regexp = config.get_delimiter()

        nameregexps = config.get_string_list('convert-to-name', [])
        self.is_name_regexp = [re.compile(r) for r in nameregexps]



    def __call__(self, obj: ProcessInfo) -> None:
        if not obj.address:
            return

        new_address: List[PlaceName] = []
        for item in obj.address:
            if self.filter_kind(item.kind):
                if self._treat_as_name(item.name):
                    obj.names.append(item.clone(kind='housenumber'))
                else:
                    new_address.extend(item.clone(kind='housenumber', name=n)
                                       for n in self.sanitize(item.name))
            else:
                # Don't touch other address items.
                new_address.append(item)

        obj.address = new_address


    def sanitize(self, value: str) -> Iterator[str]:
        """ Extract housenumbers in a regularized format from an OSM value.

            The function works as a generator that yields all valid housenumbers
            that can be created from the value.
        """
        for hnr in self.split_regexp.split(value):
            if hnr:
                yield from self._regularize(hnr)


    def _regularize(self, hnr: str) -> Iterator[str]:
        yield hnr


    def _treat_as_name(self, housenumber: str) -> bool:
        return any(r.fullmatch(housenumber) is not None for r in self.is_name_regexp)


def create(config: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """ Create a housenumber processing function.
    """

    return _HousenumberSanitizer(config)
