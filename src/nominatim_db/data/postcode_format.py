# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for formatting postcodes according to their country-specific
format.
"""
from typing import Any, Mapping, Optional, Protocol
import dataclasses
import re

from ..errors import UsageError
from . import country_info


@dataclasses.dataclass
class PostcodeMatch:
    norm: str
    extent: int


class CountryPostcodeMatcher(Protocol):
    """ Matches and formats a postcode according to a format definition
        of the given country.
    """

    def match(self, postcode: str) -> Optional[PostcodeMatch]:
        """ Match the given postcode against the postcode pattern for this
            matcher. Returns a `re.Match` object if the match was successful
            and None otherwise.
        """


class SimplePostcodeMatcher:
    """ Matches and formats a postcode according to a single format definition
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

        self.extent = int(config.get('extent', 5000))

    def match(self, postcode: str) -> Optional[PostcodeMatch]:
        # Upper-case, strip spaces and leading country code.
        normalized = self.norm_pattern.fullmatch(postcode.upper())

        if normalized:
            match = self.pattern.fullmatch(normalized.group(1))
            if match is None or self.zero_pattern.match(match.string):
                return None
            return PostcodeMatch(norm=match.expand(self.output), extent=self.extent)

        return None


class ListPostcodeMatcher:
    """ Matcher which allows to have multiple postcode patterns in a country.
    """
    def __init__(self, country_code: str, config: list[Any]) -> None:
        self.matchers = [SimplePostcodeMatcher(country_code, p) for p in config]

    def match(self, postcode: str) -> Optional[PostcodeMatch]:
        for m in self.matchers:
            if (pm := m.match(postcode)) is not None:
                return pm

        return None


class PostcodeFormatter:
    """ Container for different postcode formats of the world and
        access functions.
    """
    def __init__(self) -> None:
        # Objects without a country code can't have a postcode per definition.
        self.country_without_postcode: set[Optional[str]] = {None}
        self.country_matcher: dict[str, CountryPostcodeMatcher] = {}
        self.default_matcher = SimplePostcodeMatcher('', {'pattern': '.*'})
        self.postcode_extent: dict[Optional[str], int] = {}

        for ccode, prop in country_info.iterate('postcode'):
            if prop is False:
                self.country_without_postcode.add(ccode)
            elif isinstance(prop, dict):
                self.country_matcher[ccode] = SimplePostcodeMatcher(ccode, prop)
            elif isinstance(prop, list):
                self.country_matcher[ccode] = ListPostcodeMatcher(ccode, prop)
            else:
                raise UsageError(f"Invalid entry 'postcode' for country '{ccode}'")

    def set_default_pattern(self, pattern: str) -> None:
        """ Set the postcode match pattern to use, when a country does not
            have a specific pattern.
        """
        self.default_matcher = SimplePostcodeMatcher('', {'pattern': pattern})

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

    def match(self, country_code: Optional[str], postcode: str) -> Optional[PostcodeMatch]:
        """ Match the given postcode against the postcode pattern for this
            matcher. Returns a `re.Match` object if the country has a pattern
            and the match was successful or None if the match failed.
        """
        if (matcher := self.get_matcher(country_code)):
            return matcher.match(postcode)

        return None
