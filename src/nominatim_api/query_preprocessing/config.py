# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Configuration for query preprocessors.
"""
from typing import Any, TypeVar
from collections import UserDict

from ..errors import UsageError

T = TypeVar('T')


class QueryConfig(UserDict[str, Any]):
    """ The `QueryConfig` class is a read-only dictionary
        with configuration options for the preprocessor.
        In addition to the usual dictionary functions, the class provides
        accessors to standard preprocessor options that are used by many of the
        preprocessors.
    """

    def require_typed(self, param: str, dtype: type[T]) -> T:
        """ Return the value for the given parameter.
            Raises a UsageError if the parameter is not present or
            of the wrong type.
        """
        result = self.get(param)

        if result is None:
            raise UsageError(f"Parameter '{param}' missing.")

        if not isinstance(result, dtype):
            raise UsageError(f"Parameter '{param}' must be of type {dtype.__name__}")

        return result
