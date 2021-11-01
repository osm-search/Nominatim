"""
Version information for Nominatim.
"""

# Version information: major, minor, patch level, database patch level
#
# The first three numbers refer to the last released version.
#
# The database patch level tracks important changes between releases
# and must always be increased when there is a change to the database or code
# that requires a migration.
# Released versions always have a database patch level of 0.
NOMINATIM_VERSION = (4, 0, 0, 0)

POSTGRESQL_REQUIRED_VERSION = (9, 5)
POSTGIS_REQUIRED_VERSION = (2, 2)
