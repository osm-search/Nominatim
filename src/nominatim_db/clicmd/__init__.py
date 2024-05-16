# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Subcommand definitions for the command-line tool.
"""
# mypy and pylint disagree about the style of explicit exports,
# see https://github.com/PyCQA/pylint/issues/6006.
# pylint: disable=useless-import-alias

from .setup import SetupAll as SetupAll
from .replication import UpdateReplication as UpdateReplication
from .api import (APISearch as APISearch,
                  APIReverse as APIReverse,
                  APILookup as APILookup,
                  APIDetails as APIDetails,
                  APIStatus as APIStatus)
from .index import UpdateIndex as UpdateIndex
from .refresh import UpdateRefresh as UpdateRefresh
from .add_data import UpdateAddData as UpdateAddData
from .admin import AdminFuncs as AdminFuncs
from .freeze import SetupFreeze as SetupFreeze
from .special_phrases import ImportSpecialPhrases as ImportSpecialPhrases
from .export import QueryExport as QueryExport
from .convert import ConvertDB as ConvertDB
