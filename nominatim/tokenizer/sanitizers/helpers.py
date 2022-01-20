# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for sanitizers.
"""
import re

from nominatim.errors import UsageError

def create_split_regex(config, default=',;'):
    """ Converts the 'delimiter' parameter in the configuration into a
        compiled regular expression that can be used to split the names on the
        delimiters. The regular expression makes sure that the resulting names
        are stripped and that repeated delimiters
        are ignored but it will still create empty fields on occasion. The
        code needs to filter those.

        The 'default' parameter defines the delimiter set to be used when
        not explicitly configured.
    """
    delimiter_set = set(config.get('delimiters', default))
    if not delimiter_set:
        raise UsageError("Empty 'delimiter' parameter not allowed for sanitizer.")

    return re.compile('\\s*[{}]+\\s*'.format(''.join('\\' + d for d in delimiter_set)))
