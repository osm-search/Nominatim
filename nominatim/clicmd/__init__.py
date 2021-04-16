"""
Subcommand definitions for the command-line tool.
"""

from nominatim.clicmd.setup import SetupAll
from nominatim.clicmd.replication import UpdateReplication
from nominatim.clicmd.api import APISearch, APIReverse, APILookup, APIDetails, APIStatus
from nominatim.clicmd.index import UpdateIndex
from nominatim.clicmd.refresh import UpdateRefresh
from nominatim.clicmd.admin import AdminFuncs
from nominatim.clicmd.freeze import SetupFreeze
from nominatim.clicmd.special_phrases import ImportSpecialPhrases
