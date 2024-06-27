# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Type definitions for typing annotations.

Complex type definitions are moved here, to keep the source files readable.
"""
from typing import Union, TYPE_CHECKING

# pylint: disable=missing-class-docstring,useless-import-alias

# SQLAlchemy introduced generic types in version 2.0 making typing
# incompatible with older versions. Add wrappers here so we don't have
# to litter the code with bare-string types.

if TYPE_CHECKING:
    from typing import Any
    import sqlalchemy as sa
    import os
    from typing_extensions import (TypeAlias as TypeAlias)
else:
    TypeAlias = str

StrPath = Union[str, 'os.PathLike[str]']

SaLambdaSelect: TypeAlias = 'Union[sa.Select[Any], sa.StatementLambdaElement]'
SaSelect: TypeAlias = 'sa.Select[Any]'
SaScalarSelect: TypeAlias = 'sa.ScalarSelect[Any]'
SaRow: TypeAlias = 'sa.Row[Any]'
SaColumn: TypeAlias = 'sa.ColumnElement[Any]'
SaExpression: TypeAlias = 'sa.ColumnElement[bool]'
SaLabel: TypeAlias = 'sa.Label[Any]'
SaFromClause: TypeAlias = 'sa.FromClause'
SaSelectable: TypeAlias = 'sa.Selectable'
SaBind: TypeAlias = 'sa.BindParameter[Any]'
SaDialect: TypeAlias = 'sa.Dialect'
