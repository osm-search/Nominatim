# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Subcommand definitions for the command-line tool.
"""
# mypy and pylint disagree about the style of explicit exports,
# see https://github.com/PyCQA/pylint/issues/6006.
# pylint: disable=useless-import-alias

from nominatim.clicmd.setup import SetupAll as SetupAll
from nominatim.clicmd.replication import UpdateReplication as UpdateReplication
from nominatim.clicmd.api import (APISearch as APISearch,
                                  APIReverse as APIReverse,
                                  APILookup as APILookup,
                                  APIDetails as APIDetails,
                                  APIStatus as APIStatus)
from nominatim.clicmd.index import UpdateIndex as UpdateIndex
from nominatim.clicmd.refresh import UpdateRefresh as UpdateRefresh
from nominatim.clicmd.add_data import UpdateAddData as UpdateAddData
from nominatim.clicmd.admin import AdminFuncs as AdminFuncs
from nominatim.clicmd.freeze import SetupFreeze as SetupFreeze
from nominatim.clicmd.special_phrases import ImportSpecialPhrases as ImportSpecialPhrases
