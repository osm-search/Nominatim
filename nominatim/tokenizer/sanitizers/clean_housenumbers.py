# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer that cleans and normalizes housenumbers.

Arguments:
    delimiters: Define the set of characters to be used for
                splitting a list of housenumbers into parts. (default: ',;')

"""
from nominatim.tokenizer.sanitizers.helpers import create_split_regex

class _HousenumberSanitizer:

    def __init__(self, config):
        self.kinds = config.get('filter-kind', ('housenumber', ))
        self.split_regexp = create_split_regex(config)


    def __call__(self, obj):
        if not obj.address:
            return

        new_address = []
        for item in obj.address:
            if item.kind in self.kinds:
                new_address.extend(item.clone(kind='housenumber', name=n) for n in self.sanitize(item.name))
            else:
                # Don't touch other address items.
                new_address.append(item)

        obj.address = new_address


    def sanitize(self, value):
        """ Extract housenumbers in a regularized format from an OSM value.

            The function works as a generator that yields all valid housenumbers
            that can be created from the value.
        """
        for hnr in self.split_regexp.split(value):
            if hnr:
                yield from self._regularize(hnr)


    def _regularize(self, hnr):
        yield hnr


def create(config):
    """ Create a housenumber processing function.
    """

    return _HousenumberSanitizer(config)
