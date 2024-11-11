# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Subcommand definitions for the command-line tool.
"""

from .setup import SetupAll as SetupAll
from .replication import UpdateReplication as UpdateReplication
from .index import UpdateIndex as UpdateIndex
from .refresh import UpdateRefresh as UpdateRefresh
from .add_data import UpdateAddData as UpdateAddData
from .admin import AdminFuncs as AdminFuncs
from .freeze import SetupFreeze as SetupFreeze
from .special_phrases import ImportSpecialPhrases as ImportSpecialPhrases
