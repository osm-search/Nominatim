# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Subcommand definitions for the command-line tool.
"""

from nominatim.clicmd.setup import SetupAll
from nominatim.clicmd.replication import UpdateReplication
from nominatim.clicmd.api import APISearch, APIReverse, APILookup, APIDetails, APIStatus
from nominatim.clicmd.index import UpdateIndex
from nominatim.clicmd.refresh import UpdateRefresh
from nominatim.clicmd.add_data import UpdateAddData
from nominatim.clicmd.admin import AdminFuncs
from nominatim.clicmd.freeze import SetupFreeze
from nominatim.clicmd.special_phrases import ImportSpecialPhrases
from nominatim.clicmd.get_version import Version