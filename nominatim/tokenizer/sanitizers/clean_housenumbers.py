# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer that cleans and normalizes housenumbers.
"""
import re

class _HousenumberSanitizer:

    def __init__(self, config):
        pass


    def __call__(self, obj):
        if not obj.address:
            return

        new_address = []
        for item in obj.address:
            if item.kind in ('housenumber', 'streetnumber', 'conscriptionnumber'):
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
        for hnr in self._split_number(value):
            yield from self._regularize(hnr)


    def _split_number(self, hnr):
        for part in re.split(r'[;,]', hnr):
            yield part.strip()


    def _regularize(self, hnr):
        yield hnr


def create(config):
    """ Create a housenumber processing function.
    """

    return _HousenumberSanitizer(config)
