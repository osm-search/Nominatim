# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for formatting postcodes according to their country-specific
format.
"""
import re

from nominatim.errors import UsageError
from nominatim.data import country_info

class CountryPostcodeMatcher:
    """ Matches and formats a postcode according to a format definition
        of the given country.
    """
    def __init__(self, country_code, config):
        if 'pattern' not in config:
            raise UsageError("Field 'pattern' required for 'postcode' "
                             f"for country '{country_code}'")

        pc_pattern = config['pattern'].replace('d', '[0-9]').replace('l', '[A-Z]')

        self.norm_pattern = re.compile(f'\\s*(?:{country_code.upper()}[ -]?)?(.*)\\s*')
        self.pattern = re.compile(pc_pattern)

        self.output = config.get('output', r'\g<0>')


    def match(self, postcode):
        """ Match the given postcode against the postcode pattern for this
            matcher. Returns a `re.Match` object if the match was successful
            and None otherwise.
        """
        # Upper-case, strip spaces and leading country code.
        normalized = self.norm_pattern.fullmatch(postcode.upper())

        if normalized:
            return self.pattern.fullmatch(normalized.group(1))

        return None


    def normalize(self, match):
        """ Return the default format of the postcode for the given match.
            `match` must be a `re.Match` object previously returned by
            `match()`
        """
        return match.expand(self.output)


class PostcodeFormatter:
    """ Container for different postcode formats of the world and
        access functions.
    """
    def __init__(self):
        # Objects without a country code can't have a postcode per definition.
        self.country_without_postcode = {None}
        self.country_matcher = {}
        self.default_matcher = CountryPostcodeMatcher('', {'pattern': '.*'})

        for ccode, prop in country_info.iterate('postcode'):
            if prop is False:
                self.country_without_postcode.add(ccode)
            elif isinstance(prop, dict):
                self.country_matcher[ccode] = CountryPostcodeMatcher(ccode, prop)
            else:
                raise UsageError(f"Invalid entry 'postcode' for country '{ccode}'")


    def set_default_pattern(self, pattern):
        """ Set the postcode match pattern to use, when a country does not
            have a specific pattern or is marked as country without postcode.
        """
        self.default_matcher = CountryPostcodeMatcher('', {'pattern': pattern})


    def get_matcher(self, country_code):
        """ Return the CountryPostcodeMatcher for the given country.
            Returns None if the country doesn't have a postcode and the
            default matcher if there is no specific matcher configured for
            the country.
        """
        if country_code in self.country_without_postcode:
            return None

        return self.country_matcher.get(country_code, self.default_matcher)


    def match(self, country_code, postcode):
        """ Match the given postcode against the postcode pattern for this
            matcher. Returns a `re.Match` object if the country has a pattern
            and the match was successful or None if the match failed.
        """
        if country_code in self.country_without_postcode:
            return None

        return self.country_matcher.get(country_code, self.default_matcher).match(postcode)


    def normalize(self, country_code, match):
        """ Return the default format of the postcode for the given match.
            `match` must be a `re.Match` object previously returned by
            `match()`
        """
        return self.country_matcher.get(country_code, self.default_matcher).normalize(match)
