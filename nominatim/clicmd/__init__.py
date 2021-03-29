"""
Subcommand definitions for the command-line tool.
"""

from .setup import SetupAll
from .replication import UpdateReplication
from .api import APISearch, APIReverse, APILookup, APIDetails, APIStatus
from .index import UpdateIndex
from .refresh import UpdateRefresh
from .admin import AdminFuncs
from .freeze import SetupFreeze
from .transition import AdminTransition
from .special_phrases import ImportSpecialPhrases
