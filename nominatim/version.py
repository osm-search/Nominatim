# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Version information for Nominatim.
"""
from typing import Optional, NamedTuple

class NominatimVersion(NamedTuple):
    """ Version information for Nominatim. We follow semantic versioning.

        Major, minor and patch_level refer to the last released version.
        The database patch level tracks important changes between releases
        and must always be increased when there is a change to the database or code
        that requires a migration.

        When adding a migration on the development branch, raise the patch level
        to 99 to make sure that the migration is applied when updating from a
        patch release to the next minor version. Patch releases usually shouldn't
        have migrations in them. When they are needed, then make sure that the
        migration can be reapplied and set the migration version to the appropriate
        patch level when cherry-picking the commit with the migration.
    """

    major: int
    minor: int
    patch_level: int
    db_patch_level: int

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch_level}-{self.db_patch_level}"


NOMINATIM_VERSION = NominatimVersion(4, 2, 99, 0)

POSTGRESQL_REQUIRED_VERSION = (9, 6)
POSTGIS_REQUIRED_VERSION = (2, 2)

# Cmake sets a variable @GIT_HASH@ by executing 'git --log'. It is not run
# on every execution of 'make'.
# cmake/tool-installed.tmpl is used to build the binary 'nominatim'. Inside
# there is a call to set the variable value below.
GIT_COMMIT_HASH : Optional[str] = None


def parse_version(version: str) -> NominatimVersion:
    """ Parse a version string into a version consisting of a tuple of
        four ints: major, minor, patch level, database patch level

        This is the reverse operation of `version_str()`.
    """
    parts = version.split('.')
    return NominatimVersion(*[int(x) for x in parts[:2] + parts[2].split('-')])
