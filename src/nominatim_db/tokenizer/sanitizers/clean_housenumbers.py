# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer that preprocesses address tags for house numbers. The sanitizer
allows to

* define which tags are to be considered house numbers (see 'filter-kind')
* split house number lists into individual numbers (see 'delimiters')
* expand interpolated house numbers

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
    expand-interpolations: When true, expand house number ranges to separate numbers
                           when an 'interpolation' is present. (default: true)

"""
from typing import Iterator, Iterable, Union
import re

from ...data.place_name import PlaceNames
from .base import ProcessInfo, SanitizerFunc
from .config import SanitizerConfig

RANGE_REGEX = re.compile(r'\d+-\d+')


class _HousenumberSanitizer:

    def __init__(self, config: SanitizerConfig) -> None:
        self.filter_kind = config.get_filter('filter-kind', ['housenumber'])
        self.split_regexp = config.get_delimiter()

        self.filter_name = config.get_filter('convert-to-name', 'FAIL_ALL')
        self.expand_interpolations = config.get_bool('expand-interpolations', True)

    def __call__(self, obj: ProcessInfo) -> None:
        if not obj.address:
            return

        itype: Union[int, str, None] = None
        if self.expand_interpolations:
            itype = next((i.name for i in obj.address if i.kind == 'interpolation'), None)
            if itype is not None:
                if itype == 'all':
                    itype = 1
                elif len(itype) == 1 and itype.isdecimal():
                    itype = int(itype)
                elif itype not in ('odd', 'even'):
                    itype = None

        new_address: PlaceNames = []
        for item in obj.address:
            if self.filter_kind(item.kind):
                if itype is not None and RANGE_REGEX.fullmatch(item.name):
                    hnrs = self._expand_range(itype, item.name)
                    if hnrs:
                        new_address.extend(item.clone(kind='housenumber', name=str(hnr))
                                           for hnr in hnrs)
                        continue

                if self.filter_name(item.name):
                    obj.names.append(item.clone(kind='housenumber'))
                else:
                    new_address.extend(item.clone(kind='housenumber', name=n)
                                       for n in self.sanitize(item.name))
            elif item.kind != 'interpolation':
                # Ignore interpolation, otherwise don't touch other address items.
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

    def _expand_range(self, itype: Union[str, int], hnr: str) -> Iterable[int]:
        first, last = (int(i) for i in hnr.split('-'))

        if isinstance(itype, int):
            step = itype
        else:
            step = 2
            if (itype == 'even' and first % 2 == 1)\
               or (itype == 'odd' and first % 2 == 0):
                first += 1

        if (last + 1 - first) / step < 10:
            return range(first, last + 1, step)

        return []


def create(config: SanitizerConfig) -> SanitizerFunc:
    """ Create a housenumber processing function.
    """

    return _HousenumberSanitizer(config)
