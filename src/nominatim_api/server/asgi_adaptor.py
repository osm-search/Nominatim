# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Base abstraction for implementing based on different ASGI frameworks.
"""
from typing import Optional, Any, NoReturn, Callable
import abc
import math

from ..config import Configuration
from ..core import NominatimAPIAsync
from ..result_formatting import FormatDispatcher
from .content_types import CONTENT_TEXT


class ASGIAdaptor(abc.ABC):
    """ Adapter class for the different ASGI frameworks.
        Wraps functionality over concrete requests and responses.
    """
    content_type: str = CONTENT_TEXT

    @abc.abstractmethod
    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """ Return an input parameter as a string. If the parameter was
            not provided, return the 'default' value.
        """

    @abc.abstractmethod
    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """ Return a HTTP header parameter as a string. If the parameter was
            not provided, return the 'default' value.
        """

    @abc.abstractmethod
    def error(self, msg: str, status: int = 400) -> Exception:
        """ Construct an appropriate exception from the given error message.
            The exception must result in a HTTP error with the given status.
        """

    @abc.abstractmethod
    def create_response(self, status: int, output: str, num_results: int) -> Any:
        """ Create a response from the given parameters. The result will
            be returned by the endpoint functions. The adaptor may also
            return None when the response is created internally with some
            different means.

            The response must return the HTTP given status code 'status', set
            the HTTP content-type headers to the string provided and the
            body of the response to 'output'.
        """

    @abc.abstractmethod
    def base_uri(self) -> str:
        """ Return the URI of the original request.
        """

    @abc.abstractmethod
    def config(self) -> Configuration:
        """ Return the current configuration object.
        """

    @abc.abstractmethod
    def formatting(self) -> FormatDispatcher:
        """ Return the formatting object to use.
        """

    def get_int(self, name: str, default: Optional[int] = None) -> int:
        """ Return an input parameter as an int. Raises an exception if
            the parameter is given but not in an integer format.

            If 'default' is given, then it will be returned when the parameter
            is missing completely. When 'default' is None, an error will be
            raised on a missing parameter.
        """
        value = self.get(name)

        if value is None:
            if default is not None:
                return default

            self.raise_error(f"Parameter '{name}' missing.")

        try:
            intval = int(value)
        except ValueError:
            self.raise_error(f"Parameter '{name}' must be a number.")

        return intval

    def get_float(self, name: str, default: Optional[float] = None) -> float:
        """ Return an input parameter as a flaoting-point number. Raises an
            exception if the parameter is given but not in an float format.

            If 'default' is given, then it will be returned when the parameter
            is missing completely. When 'default' is None, an error will be
            raised on a missing parameter.
        """
        value = self.get(name)

        if value is None:
            if default is not None:
                return default

            self.raise_error(f"Parameter '{name}' missing.")

        try:
            fval = float(value)
        except ValueError:
            self.raise_error(f"Parameter '{name}' must be a number.")

        if math.isnan(fval) or math.isinf(fval):
            self.raise_error(f"Parameter '{name}' must be a number.")

        return fval

    def get_bool(self, name: str, default: Optional[bool] = None) -> bool:
        """ Return an input parameter as bool. Only '0' is accepted as
            an input for 'false' all other inputs will be interpreted as 'true'.

            If 'default' is given, then it will be returned when the parameter
            is missing completely. When 'default' is None, an error will be
            raised on a missing parameter.
        """
        value = self.get(name)

        if value is None:
            if default is not None:
                return default

            self.raise_error(f"Parameter '{name}' missing.")

        return value != '0'

    def raise_error(self, msg: str, status: int = 400) -> NoReturn:
        """ Raise an exception resulting in the given HTTP status and
            message. The message will be formatted according to the
            output format chosen by the request.
        """
        raise self.error(self.formatting().format_error(self.content_type, msg, status),
                         status)


EndpointFunc = Callable[[NominatimAPIAsync, ASGIAdaptor], Any]
