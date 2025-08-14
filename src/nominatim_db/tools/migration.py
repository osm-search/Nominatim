# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for database migration to newer software versions.
"""
from typing import List, Tuple, Callable, Any
import logging

from ..errors import UsageError
from ..config import Configuration
from ..db import properties
from ..db.connection import connect, Connection, \
                            table_exists, register_hstore
from ..db.sql_preprocessor import SQLPreprocessor
from ..version import NominatimVersion, NOMINATIM_VERSION, parse_version
from ..tokenizer import factory as tokenizer_factory
from . import refresh

LOG = logging.getLogger()

_MIGRATION_FUNCTIONS: List[Tuple[NominatimVersion, Callable[..., None]]] = []


def migrate(config: Configuration, paths: Any) -> int:
    """ Check for the current database version and execute migrations,
        if necesssary.
    """
    with connect(config.get_libpq_dsn()) as conn:
        register_hstore(conn)
        if table_exists(conn, 'nominatim_properties'):
            db_version_str = properties.get_property(conn, 'database_version')
        else:
            db_version_str = None

        if db_version_str is not None:
            db_version = parse_version(db_version_str)
        else:
            db_version = None

        if db_version is None or db_version < (4, 3, 0, 0):
            LOG.fatal('Your database version is older than 4.3. '
                      'Direct migration is not possible.\n'
                      'You should strongly consider a reimport. If that is not possible\n'
                      'please upgrade to 4.3 first and then to the newest version.')
            raise UsageError('Migration not possible.')

        if db_version == NOMINATIM_VERSION:
            LOG.warning("Database already at latest version (%s)", db_version_str)
            return 0

        LOG.info("Detected database version: %s", db_version_str)

        for version, func in _MIGRATION_FUNCTIONS:
            if db_version < version:
                title = func.__doc__ or ''
                LOG.warning("Running: %s (%s)", title.split('\n', 1)[0], version)
                kwargs = dict(conn=conn, config=config, paths=paths)
                func(**kwargs)
                conn.commit()

        LOG.warning('Updating SQL functions.')
        refresh.create_functions(conn, config)
        tokenizer = tokenizer_factory.get_tokenizer_for_db(config)
        tokenizer.update_sql_functions(config)

        properties.set_property(conn, 'database_version', str(NOMINATIM_VERSION))

        conn.commit()

    return 0


def _migration(major: int, minor: int, patch: int = 0,
               dbpatch: int = 0) -> Callable[[Callable[..., None]], Callable[..., None]]:
    """ Decorator for a single migration step. The parameters describe the
        version after which the migration is applicable, i.e before changing
        from the given version to the next, the migration is required.

        All migrations are run in the order in which they are defined in this
        file. Do not run global SQL scripts for migrations as you cannot be sure
        that these scripts do the same in later versions.

        Functions will always be reimported in full at the end of the migration
        process, so the migration functions may leave a temporary state behind
        there.
    """
    def decorator(func: Callable[..., None]) -> Callable[..., None]:
        version = NominatimVersion(major, minor, patch, dbpatch)
        _MIGRATION_FUNCTIONS.append((version, func))
        return func

    return decorator


@_migration(4, 4, 99, 0)
def create_postcode_area_lookup_index(conn: Connection, **_: Any) -> None:
    """ Create index needed for looking up postcode areas from postocde points.
    """
    with conn.cursor() as cur:
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_placex_postcode_areas
                       ON placex USING BTREE (country_code, postcode)
                       WHERE osm_type = 'R' AND class = 'boundary' AND type = 'postal_code'
                    """)


@_migration(4, 4, 99, 1)
def create_postcode_parent_index(conn: Connection, **_: Any) -> None:
    """ Create index needed for updating postcodes when a parent changes.
    """
    if table_exists(conn, 'planet_osm_ways'):
        with conn.cursor() as cur:
            cur.execute("""CREATE INDEX IF NOT EXISTS
                             idx_location_postcode_parent_place_id
                             ON location_postcode USING BTREE (parent_place_id)""")


@_migration(5, 1, 99, 0)
def create_place_entrance_table(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Add the place_entrance table to store entrance nodes
    """
    sqlp = SQLPreprocessor(conn, config)
    sqlp.run_string(conn, """
        -- Table to store location of entrance nodes
        DROP TABLE IF EXISTS place_entrance;
        CREATE TABLE place_entrance (
          place_id BIGINT NOT NULL,
          entrances JSONB NOT NULL
          );
        CREATE UNIQUE INDEX idx_place_entrance_place_id ON place_entrance
          USING BTREE (place_id) {{db.tablespace.search_index}};
        GRANT SELECT ON place_entrance TO "{{config.DATABASE_WEBUSER}}" ;

        -- Create an index on the place table for lookups to populate the entrance
        -- table
        CREATE INDEX IF NOT EXISTS idx_place_entrance_lookup ON place
          USING BTREE (osm_id)
          WHERE class IN ('routing:entrance', 'entrance');
          """)
