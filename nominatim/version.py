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
from nominatim.db import properties
from nominatim.db.connection import connect

NOMINATIM_VERSION = (4, 0, 99, 5)

POSTGRESQL_REQUIRED_VERSION = (9, 5)
POSTGIS_REQUIRED_VERSION = (2, 2)

class Version:
    """\
    Display version information.
    """

    @staticmethod
    def add_args(parser):
        pass

    @staticmethod
    def run(args):
        print(f'Nominatim {Version._format_tuple(NOMINATIM_VERSION)}',
              f'PostgreSQL required version {Version._format_tuple(POSTGRESQL_REQUIRED_VERSION)}',
              f'PostGIS required version {Version._format_tuple(POSTGIS_REQUIRED_VERSION)}',
              sep="\n")
        if args.verbose > 1:
            with connect(args.config.get_libpq_dsn()) as conn:
                if conn.table_exists('nominatim_properties'):
                    db_version_str = properties.get_property(conn, 'database_version')
                else:
                    db_version_str = None

                if db_version_str is not None:
                    print(f'Current database version: {db_version_str}')
                else:
                    print('Could not detect current database version.')

        return 0

    @staticmethod
    def _format_tuple(int_tuple):
        """\
        Formats a tuple of integers into a period-separated string version number.
        """
        return '.'.join([str(i) for i in int_tuple])
