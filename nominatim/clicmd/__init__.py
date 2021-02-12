"""
Subcommand definitions for the command-line tool.
"""

from .replication import UpdateReplication
from .api import APISearch, APIReverse, APILookup, APIDetails, APIStatus
from .index import UpdateIndex
from .refresh import UpdateRefresh
from .admin import AdminFuncs
