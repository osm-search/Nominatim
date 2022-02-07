# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer that splits lists of names into their components.

Arguments:
    delimiters: Define the set of characters to be used for
                splitting the list. (default: ',;')
"""
def create(config):
    """ Create a name processing function that splits name values with
        multiple values into their components.
    """
    regexp = config.get_delimiter()

    def _process(obj):
        if not obj.names:
            return

        new_names = []
        for name in obj.names:
            split_names = regexp.split(name.name)
            if len(split_names) == 1:
                new_names.append(name)
            else:
                new_names.extend(name.clone(name=n) for n in split_names if n)

        obj.names = new_names

    return _process
