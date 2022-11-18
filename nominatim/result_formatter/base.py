# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper classes and function for writing result formatting modules.
"""
from typing import Type, TypeVar, Dict, Mapping, List, Callable, Generic, Any
from collections import defaultdict

T = TypeVar('T') # pylint: disable=invalid-name
FormatFunc = Callable[[T], str]

class ResultFormatter(Generic[T]):
    """ This class dispatches format calls to the appropriate formatting
        function previously defined with the `format_func` decorator.
    """

    def __init__(self, funcs: Mapping[str, FormatFunc[T]]) -> None:
        self.functions = funcs


    def list_formats(self) -> List[str]:
        """ Return a list of formats supported by this formatter.
        """
        return list(self.functions.keys())


    def format(self, result: T, fmt: str) -> str:
        """ Convert the given result into a string using the given format.

            The format is expected to be in the list returned by
            `list_formats()`.
        """
        return self.functions[fmt](result)


class FormatDispatcher:
    """ A factory class for result formatters.
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


    def __call__(self, result_class: Type[T]) -> ResultFormatter[T]:
        """ Create an instance of a format class for the given result type.
        """
        return ResultFormatter(self.format_functions[result_class])
