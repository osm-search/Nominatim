# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Configuration for Sanitizers.
"""
from typing import Sequence, Union, Optional, Pattern, Callable, Any
from collections import UserDict
import re

from ...errors import UsageError


class SanitizerConfig(UserDict[str, Any]):
    """ The `SanitizerConfig` class is a read-only dictionary
        with configuration options for the sanitizer.
        In addition to the usual dictionary functions, the class provides
        accessors to standard sanitizer options that are used by many of the
        sanitizers.
    """

    def get_pattern(self, param: str, default: Optional[str] = None,
                    flags: int = 0) -> re.Pattern[str]:
        """ Extract a configuration parameter as a regular expression
            and return a compiled regex pattern. Use 'flags' to initiate
            the pattern with different compile flags.

            If 'default' is not given, then the parameter must exist
            or a UsageError is thrown.
        """
        strpattern = self.data.get(param, default)

        if strpattern is None:
            raise UsageError(f"Parameter {param} is missing but required.")

        if not isinstance(strpattern, str):
            raise UsageError(f"Parameter {param} must be a string.")

        return re.compile(strpattern, flags=flags)

    def get_string_list(self, param: str, default: Sequence[str] = tuple()) -> Sequence[str]:
        """ Extract a configuration parameter as a string list.

            Arguments:
                param: Name of the configuration parameter.
                default: Takes a tuple or list of strings which will
                         be returned if the parameter is missing in the
                         sanitizer configuration.
                         Note that if this default parameter is not
                         provided then an empty list is returned.

            Returns:
                If the parameter value is a simple string, it is returned as a
                    one-item list. If the parameter value does not exist, the given
                    default is returned. If the parameter value is a list, it is
                    checked to contain only strings before being returned.
        """
        values = self.data.get(param, None)

        if values is None:
            return list(default)

        if isinstance(values, str):
            return [values] if values else []

        if not isinstance(values, (list, tuple)):
            raise UsageError(f"Parameter '{param}' must be string or list of strings.")

        if any(not isinstance(value, str) for value in values):
            raise UsageError(f"Parameter '{param}' must be string or list of strings.")

        return values

    def get_bool(self, param: str, default: Optional[bool] = None) -> bool:
        """ Extract a configuration parameter as a boolean.

            Arguments:
                param: Name of the configuration parameter. The parameter must
                       contain one of the yaml boolean values or an
                       UsageError will be raised.
                default: Value to return, when the parameter is missing.
                         When set to `None`, the parameter must be defined.

            Returns:
                Boolean value of the given parameter.
        """
        value = self.data.get(param, default)

        if not isinstance(value, bool):
            raise UsageError(f"Parameter '{param}' must be a boolean value ('yes' or 'no').")

        return value

    def get_delimiter(self, default: str = ',;') -> Pattern[str]:
        """ Return the 'delimiters' parameter in the configuration as a
            compiled regular expression that can be used to split strings on
            these delimiters.

            Arguments:
                default: Delimiters to be used when 'delimiters' parameter
                         is not explicitly configured.

            Returns:
                A regular expression pattern which can be used to
                    split a string. The regular expression makes sure that the
                    resulting names are stripped and that repeated delimiters
                    are ignored. It may still create empty fields on occasion. The
                    code needs to filter those.
        """
        delimiter_set = set(self.data.get('delimiters', default))
        if not delimiter_set:
            raise UsageError("Empty 'delimiter' parameter not allowed for sanitizer.")

        return re.compile('\\s*[{}]+\\s*'.format(''.join('\\' + d for d in delimiter_set)))

    def get_filter(self, param: str, default: Union[str, Sequence[str]] = 'PASS_ALL'
                   ) -> Callable[[str], bool]:
        """ Returns a filter function for the given parameter of the sanitizer
            configuration.

            The value provided for the parameter in sanitizer configuration
            should be a string or list of strings, where each string is a regular
            expression. These regular expressions will later be used by the
            filter function to filter strings.

            Arguments:
                param: The parameter for which the filter function
                       will be created.
                default: Defines the behaviour of filter function if
                         parameter is missing in the sanitizer configuration.
                         Takes a string(PASS_ALL or FAIL_ALL) or a list of strings.
                         Any other value of string or an empty list is not allowed,
                         and will raise a ValueError. If the value is PASS_ALL, the filter
                         function will let all strings to pass, if the value is FAIL_ALL,
                         filter function will let no strings to pass.
                         If value provided is a list of strings each string
                         is treated as a regular expression. In this case these regular
                         expressions will be used by the filter function.
                         By default allow filter function to let all strings pass.

            Returns:
                A filter function that takes a target string as the argument and
                    returns True if it fully matches any of the regular expressions
                    otherwise returns False.
        """
        filters = self.get_string_list(param) or default

        if filters == 'PASS_ALL':
            return lambda _: True
        if filters == 'FAIL_ALL':
            return lambda _: False

        if filters and isinstance(filters, (list, tuple)):
            regexes = [re.compile(regex) for regex in filters]
            return lambda target: any(regex.fullmatch(target) for regex in regexes)

        raise ValueError("Default parameter must be a non-empty list or a string value \
                          ('PASS_ALL' or 'FAIL_ALL').")

    def get_choice(self, param: str, opt_cls: type[Any], default: Optional[int] = None) -> int:
        """ Return an integer representing a value from a fixed list of choices.

            The choices must be given in form of a class containing class constants
            of type int. The given value in the configuration must be a string which,
            after having been cnverted to upper case and hyphens having been
            replaced with underscores, corresponds to one of the class constants.
            Only values starting with an ASCII letter and containing ASCII letters
            and numbers, hyphen and underscore are accepted.

            Arguments:
                param: The parameter containing the choice variable.
                opt_cls: The class describing valid choices.
                default: Default value to use when none is supplied in the
                         configuration. Must be an integer representing one
                         of the choices. When left None (the default), then
                         the parameter is required and leaving it out will
                         throw an error.

            Returns:
                The integer with the selected choice.
        """
        value = self.data.get(param)

        if value is None:
            if default is None:
                raise UsageError(f"Parameter {param} is missing but required.")
            return default

        if not isinstance(value, str):
            raise UsageError(f"Parameter {param} must be a string.")

        value = value.upper().replace('-', '_')

        if re.fullmatch('[A-Z][A-Z0-9_]*', value) is None:
            raise UsageError(f"Invalid value for parameter {param}.")

        res = getattr(opt_cls, value, None)

        if not isinstance(res, int):
            raise UsageError(f"Invalid value for parameter {param}.")

        return res
