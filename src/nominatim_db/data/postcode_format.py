# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for formatting postcodes according to their country-specific
format.
"""
from typing import Any, Mapping, Optional, Set, Match
import re

from ..errors import UsageError
from . import country_info


class CountryPostcodeMatcher:
    """ Matches and formats a postcode according to a format definition
        of the given country.
    """
    def __init__(self, country_code: str, config: Mapping[str, Any]) -> None:
        if 'pattern' not in config:
            raise UsageError("Field 'pattern' required for 'postcode' "
                             f"for country '{country_code}'")

        pc_pattern = config['pattern'].replace('d', '[0-9]').replace('l', '[A-Z]')

        self.norm_pattern = re.compile(f'\\s*(?:{country_code.upper()}[ -]?)?({pc_pattern})\\s*')
        self.pattern = re.compile(pc_pattern)

        # We want to exclude 0000, 00-000, 000 00 etc
        self.zero_pattern = re.compile(r'^[0\- ]+$')

        self.output = config.get('output', r'\g<0>')

    def match(self, postcode: str) -> Optional[Match[str]]:
        """ Match the given postcode against the postcode pattern for this
            matcher. Returns a `re.Match` object if the match was successful
            and None otherwise.
        """
        # Upper-case, strip spaces and leading country code.
        normalized = self.norm_pattern.fullmatch(postcode.upper())

        if normalized:
            match = self.pattern.fullmatch(normalized.group(1))
            if match and self.zero_pattern.match(match.string):
                return None
            return match

        return None

    def normalize(self, match: Match[str]) -> str:
        """ Return the default format of the postcode for the given match.
            `match` must be a `re.Match` object previously returned by
            `match()`
        """
        return match.expand(self.output)


class PostcodeFormatter:
    """ Container for different postcode formats of the world and
        access functions.
    """
    def __init__(self) -> None:
        # Objects without a country code can't have a postcode per definition.
        self.country_without_postcode: Set[Optional[str]] = {None}
        self.country_matcher = {}
        self.default_matcher = CountryPostcodeMatcher('', {'pattern': '.*'})
        self.postcode_extent: dict[Optional[str], int] = {}

        for ccode, prop in country_info.iterate('postcode'):
            if prop is False:
                self.country_without_postcode.add(ccode)
            elif isinstance(prop, dict):
                self.country_matcher[ccode] = CountryPostcodeMatcher(ccode, prop)
                if 'extent' in prop:
                    self.postcode_extent[ccode] = int(prop['extent'])
            else:
                raise UsageError(f"Invalid entry 'postcode' for country '{ccode}'")

    def set_default_pattern(self, pattern: str) -> None:
        """ Set the postcode match pattern to use, when a country does not
            have a specific pattern.
        """
        self.default_matcher = CountryPostcodeMatcher('', {'pattern': pattern})

    def get_matcher(self, country_code: Optional[str]) -> Optional[CountryPostcodeMatcher]:
        """ Return the CountryPostcodeMatcher for the given country.
            Returns None if the country doesn't have a postcode and the
            default matcher if there is no specific matcher configured for
            the country.
        """
        if country_code in self.country_without_postcode:
            return None

        assert country_code is not None

        return self.country_matcher.get(country_code, self.default_matcher)

    def match(self, country_code: Optional[str], postcode: str) -> Optional[Match[str]]:
        """ Match the given postcode against the postcode pattern for this
            matcher. Returns a `re.Match` object if the country has a pattern
            and the match was successful or None if the match failed.
        """
        if country_code in self.country_without_postcode:
            return None

        assert country_code is not None

        return self.country_matcher.get(country_code, self.default_matcher).match(postcode)

    def normalize(self, country_code: str, match: Match[str]) -> str:
        """ Return the default format of the postcode for the given match.
            `match` must be a `re.Match` object previously returned by
            `match()`
        """
        return self.country_matcher.get(country_code, self.default_matcher).normalize(match)

    def get_postcode_extent(self, country_code: Optional[str]) -> int:
        """ Return the extent (in m) to use for the given country. If no
            specific extent is set, then the default of 5km will be returned.
        """
        return self.postcode_extent.get(country_code, 5000)
