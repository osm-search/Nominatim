# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper classes and functions for formatting results into API responses.
"""
from typing import Type, TypeVar, Dict, List, Callable, Any, Mapping, Optional, cast
from collections import defaultdict
from pathlib import Path
import importlib.util

from .server.content_types import CONTENT_JSON

T = TypeVar('T')
FormatFunc = Callable[[T, Mapping[str, Any]], str]
ErrorFormatFunc = Callable[[str, str, int], str]


class FormatDispatcher:
    """ Container for formatting functions for results.
        Functions can conveniently be added by using decorated functions.
    """

    def __init__(self, content_types: Optional[Mapping[str, str]] = None) -> None:
        self.error_handler: ErrorFormatFunc = lambda ct, msg, status: f"ERROR {status}: {msg}"
        self.content_types: Dict[str, str] = {}
        if content_types:
            self.content_types.update(content_types)
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

    def error_format_func(self, func: ErrorFormatFunc) -> ErrorFormatFunc:
        """ Decorator for a function that formats error messages.
            There is only one error formatter per dispatcher. Using
            the decorator repeatedly will overwrite previous functions.
        """
        self.error_handler = func
        return func

    def list_formats(self, result_type: Type[Any]) -> List[str]:
        """ Return a list of formats supported by this formatter.
        """
        return list(self.format_functions[result_type].keys())

    def supports_format(self, result_type: Type[Any], fmt: str) -> bool:
        """ Check if the given format is supported by this formatter.
        """
        return fmt in self.format_functions[result_type]

    def format_result(self, result: Any, fmt: str, options: Mapping[str, Any]) -> str:
        """ Convert the given result into a string using the given format.

            The format is expected to be in the list returned by
            `list_formats()`.
        """
        return self.format_functions[type(result)][fmt](result, options)

    def format_error(self, content_type: str, msg: str, status: int) -> str:
        """ Convert the given error message into a response string
            taking the requested content_type into account.

            Change the format using the error_format_func decorator.
        """
        return self.error_handler(content_type, msg, status)

    def set_content_type(self, fmt: str, content_type: str) -> None:
        """ Set the content type for the given format. This is the string
            that will be returned in the Content-Type header of the HTML
            response, when the given format is chosen.
        """
        self.content_types[fmt] = content_type

    def get_content_type(self, fmt: str) -> str:
        """ Return the content type for the given format.

            If no explicit content type has been defined, then
            JSON format is assumed.
        """
        return self.content_types.get(fmt, CONTENT_JSON)


def load_format_dispatcher(api_name: str, project_dir: Optional[Path]) -> FormatDispatcher:
    """ Load the dispatcher for the given API.

        The function first tries to find a module api/<api_name>/format.py
        in the project directory. This file must export a single variable
        `dispatcher`.

        If the function does not exist, the default formatter is loaded.
    """
    if project_dir is not None:
        priv_module = project_dir / 'api' / api_name / 'format.py'
        if priv_module.is_file():
            spec = importlib.util.spec_from_file_location(f'api.{api_name},format',
                                                          str(priv_module))
            if spec:
                module = importlib.util.module_from_spec(spec)
                # Do not add to global modules because there is no standard
                # module name that Python can resolve.
                assert spec.loader is not None
                spec.loader.exec_module(module)

                return cast(FormatDispatcher, module.dispatch)

    return cast(FormatDispatcher,
                importlib.import_module(f'nominatim_api.{api_name}.format').dispatch)
