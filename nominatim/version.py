# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
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
#
# When adding a migration on the development branch, raise the patch level
# to 99 to make sure that the migration is applied when updating from a
# patch release to the next minor version. Patch releases usually shouldn't
# have migrations in them. When they are needed, then make sure that the
# migration can be reapplied and set the migration version to the appropriate
# patch level when cherry-picking the commit with the migration.
#
# Released versions always have a database patch level of 0.
NOMINATIM_VERSION = (4, 0, 99, 5)

POSTGRESQL_REQUIRED_VERSION = (9, 5)
POSTGIS_REQUIRED_VERSION = (2, 2)
