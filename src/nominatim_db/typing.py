# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Type definitions for typing annotations.

Complex type definitions are moved here, to keep the source files readable.
"""
from typing import Any, Union, Mapping, TypeVar, Sequence, TYPE_CHECKING


if TYPE_CHECKING:
    import os

StrPath = Union[str, 'os.PathLike[str]']

SysEnv = Mapping[str, str]

# psycopg-related types

T_ResultKey = TypeVar('T_ResultKey', int, str)


class DictCursorResult(Mapping[str, Any]):
    def __getitem__(self, x: Union[int, str]) -> Any: ...


DictCursorResults = Sequence[DictCursorResult]

if TYPE_CHECKING:
    from psycopg.abc import (QueryNoTemplate as QueryNoTemplate)
else:
    QueryNoTemplate = 'QueryNoTemplate'
