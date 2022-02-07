# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Configuration for Sanitizers.
"""
from collections import UserDict
import re

from nominatim.errors import UsageError

class SanitizerConfig(UserDict):
    """ Dictionary with configuration options for a sanitizer.

        In addition to the usualy dictionary function, the class provides
        accessors to standard sanatizer options that are used by many of the
        sanitizers.
    """

    def get_string_list(self, param, default=tuple()):
        """ Extract a configuration parameter as a string list.
            If the parameter value is a simple string, it is returned as a
            one-item list. If the parameter value does not exist, the given
            default is returned. If the parameter value is a list, it is checked
            to contain only strings before being returned.
        """
        values = self.data.get(param, None)

        if values is None:
            return None if default is None else list(default)

        if isinstance(values, str):
            return [values] if values else []

        if not isinstance(values, (list, tuple)):
            raise UsageError(f"Parameter '{param}' must be string or list of strings.")

        if any(not isinstance(value, str) for value in values):
            raise UsageError(f"Parameter '{param}' must be string or list of strings.")

        return values


    def get_delimiter(self, default=',;'):
        """ Return the 'delimiter' parameter in the configuration as a
            compiled regular expression that can be used to split the names on the
            delimiters. The regular expression makes sure that the resulting names
            are stripped and that repeated delimiters
            are ignored but it will still create empty fields on occasion. The
            code needs to filter those.

            The 'default' parameter defines the delimiter set to be used when
            not explicitly configured.
        """
        delimiter_set = set(self.data.get('delimiters', default))
        if not delimiter_set:
            raise UsageError("Empty 'delimiter' parameter not allowed for sanitizer.")

        return re.compile('\\s*[{}]+\\s*'.format(''.join('\\' + d for d in delimiter_set)))


    def get_filter_kind(self, *default):
        """ Return a filter function for the name kind from the 'filter-kind'
            config parameter. The filter functions takes a name item and returns
            True when the item passes the filter.

            If the parameter is empty, the filter lets all items pass. If the
            paramter is a string, it is interpreted as a single regular expression
            that must match the full kind string. If the parameter is a list then
            any of the regular expressions in the list must match to pass.
        """
        filters = self.get_string_list('filter-kind', default)

        if not filters:
            return lambda _: True

        regexes = [re.compile(regex) for regex in filters]

        return lambda name: any(regex.fullmatch(name.kind) for regex in regexes)
