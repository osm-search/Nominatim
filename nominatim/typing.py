# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Type definitions for typing annotations.

Complex type definitions are moved here, to keep the source files readable.
"""
from typing import Any, Union, Mapping, TypeVar, Sequence, TYPE_CHECKING

# Generics varaible names do not confirm to naming styles, ignore globally here.
# pylint: disable=invalid-name,abstract-method,multiple-statements
# pylint: disable=missing-class-docstring,useless-import-alias

if TYPE_CHECKING:
    import psycopg2.sql
    import psycopg2.extensions
    import psycopg2.extras
    import os

StrPath = Union[str, 'os.PathLike[str]']

SysEnv = Mapping[str, str]

# psycopg2-related types

Query = Union[str, bytes, 'psycopg2.sql.Composable']

T_ResultKey = TypeVar('T_ResultKey', int, str)

class DictCursorResult(Mapping[str, Any]):
    def __getitem__(self, x: Union[int, str]) -> Any: ...

DictCursorResults = Sequence[DictCursorResult]

T_cursor = TypeVar('T_cursor', bound='psycopg2.extensions.cursor')

# The following typing features require typing_extensions to work
# on all supported Python versions.
# Only require this for type checking but not for normal operations.

if TYPE_CHECKING:
    from typing_extensions import (Protocol as Protocol,
                                   Final as Final,
                                   TypedDict as TypedDict)
else:
    Protocol = object
    Final = 'Final'
    TypedDict = dict
