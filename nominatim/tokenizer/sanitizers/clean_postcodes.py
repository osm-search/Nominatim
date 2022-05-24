# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer that filters postcodes by their officially allowed pattern.

Arguments:
    convert-to-address: If set to 'yes' (the default), then postcodes that do
                        not conform with their country-specific pattern are
                        converted to an address component. That means that
                        the postcode does not take part when computing the
                        postcode centroids of a country but is still searchable.
                        When set to 'no', non-conforming postcodes are not
                        searchable either.
"""
import re

from nominatim.errors import UsageError
from nominatim.tools import country_info

class _PostcodeMatcher:
    """ Matches and formats a postcode according to the format definition.
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


class _PostcodeSanitizer:

    def __init__(self, config):
        self.convert_to_address = config.get_bool('convert-to-address', True)
        # Objects without a country code can't have a postcode per definition.
        self.country_without_postcode = {None}
        self.country_matcher = {}

        for ccode, prop in country_info.iterate('postcode'):
            if prop is False:
                self.country_without_postcode.add(ccode)
            elif isinstance(prop, dict):
                self.country_matcher[ccode] = _PostcodeMatcher(ccode, prop)
            else:
                raise UsageError(f"Invalid entry 'postcode' for country '{ccode}'")

        default_pattern = config.get('default-pattern')
        if default_pattern is not None and isinstance(default_pattern, str):
            self.default_matcher = _PostcodeMatcher('', {'pattern': default_pattern})
        else:
            self.default_matcher = None


    def __call__(self, obj):
        if not obj.address:
            return

        postcodes = ((i, o) for i, o in enumerate(obj.address) if o.kind == 'postcode')

        for pos, postcode in postcodes:
            formatted = self.scan(postcode.name, obj.place.country_code)

            if formatted is None:
                if self.convert_to_address:
                    postcode.kind = 'unofficial_postcode'
                else:
                    obj.address.pop(pos)
            else:
                postcode.name = formatted[0]
                postcode.set_attr('lookup', formatted[1])


    def scan(self, postcode, country):
        """ Check the postcode for correct formatting and return the
            normalized version. Returns None if the postcode does not
            correspond to the oficial format of the given country.
        """
        if country in self.country_without_postcode:
            return None

        matcher = self.country_matcher.get(country, self.default_matcher)
        if matcher is None:
            return postcode.upper(), ''

        match = matcher.match(postcode)
        if match is None:
            return None

        return matcher.normalize(match), ' '.join(match.groups())




def create(config):
    """ Create a housenumber processing function.
    """

    return _PostcodeSanitizer(config)
