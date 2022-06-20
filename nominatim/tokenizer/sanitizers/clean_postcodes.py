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
    default-pattern:    Pattern to use, when there is none available for the
                        country in question. Warning: will not be used for
                        objects that have no country assigned. These are always
                        assumed to have no postcode.
"""
from nominatim.data.postcode_format import PostcodeFormatter

class _PostcodeSanitizer:

    def __init__(self, config):
        self.convert_to_address = config.get_bool('convert-to-address', True)
        self.matcher = PostcodeFormatter()

        default_pattern = config.get('default-pattern')
        if default_pattern is not None and isinstance(default_pattern, str):
            self.matcher.set_default_pattern(default_pattern)


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
                postcode.set_attr('variant', formatted[1])


    def scan(self, postcode, country):
        """ Check the postcode for correct formatting and return the
            normalized version. Returns None if the postcode does not
            correspond to the oficial format of the given country.
        """
        match = self.matcher.match(country, postcode)
        if match is None:
            return None

        return self.matcher.normalize(country, match),\
               ' '.join(filter(lambda p: p is not None, match.groups()))




def create(config):
    """ Create a housenumber processing function.
    """

    return _PostcodeSanitizer(config)
