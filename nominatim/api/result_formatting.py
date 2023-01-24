# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper classes and functions for formating results into API responses.
"""
from typing import Type, TypeVar, Dict, List, Callable, Any
from collections import defaultdict

T = TypeVar('T') # pylint: disable=invalid-name
FormatFunc = Callable[[T], str]


class FormatDispatcher:
    """ Helper class to conveniently create formatting functions in
        a module using decorators.
    """

    def __init__(self) -> None:
        self.format_functions: Dict[Type[Any], Dict[str, FormatFunc[Any]]] = defaultdict(dict)


    def format_func(self, result_class: Type[T],
                    fmt: str) -> Callable[[FormatFunc[T]], FormatFunc[T]]:
        """ Decorator for a function that formats a given type of result into the
            selected format.
        """
        def decorator(func: FormatFunc[T]) -> FormatFunc[T]:
            self.format_functions[result_class][fmt] = func
            return func

        return decorator


    def list_formats(self, result_type: Type[Any]) -> List[str]:
        """ Return a list of formats supported by this formatter.
        """
        return list(self.format_functions[result_type].keys())


    def supports_format(self, result_type: Type[Any], fmt: str) -> bool:
        """ Check if the given format is supported by this formatter.
        """
        return fmt in self.format_functions[result_type]


    def format_result(self, result: Any, fmt: str) -> str:
        """ Convert the given result into a string using the given format.

            The format is expected to be in the list returned by
            `list_formats()`.
        """
        return self.format_functions[type(result)][fmt](result)
