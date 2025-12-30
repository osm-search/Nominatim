# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
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
from ..data.country_info import create_country_names, setup_country_config
from .freeze import is_frozen
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
def create_placex_entrance_table(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Add the placex_entrance table to store linked-up entrance nodes
    """
    if not table_exists(conn, 'placex_entrance'):
        sqlp = SQLPreprocessor(conn, config)
        sqlp.run_string(conn, """
            -- Table to store location of entrance nodes
            CREATE TABLE placex_entrance (
              place_id BIGINT NOT NULL,
              osm_id BIGINT NOT NULL,
              type TEXT NOT NULL,
              location GEOMETRY(Point, 4326) NOT NULL,
              extratags HSTORE
              );
            CREATE UNIQUE INDEX idx_placex_entrance_place_id_osm_id ON placex_entrance
              USING BTREE (place_id, osm_id) {{db.tablespace.search_index}};
            GRANT SELECT ON placex_entrance TO "{{config.DATABASE_WEBUSER}}" ;
              """)


@_migration(5, 1, 99, 1)
def create_place_entrance_table(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Add the place_entrance table to store incomming entrance nodes
    """
    if not table_exists(conn, 'place_entrance'):
        with conn.cursor() as cur:
            cur.execute("""
            -- Table to store location of entrance nodes
            CREATE TABLE place_entrance (
              osm_id BIGINT NOT NULL,
              type TEXT NOT NULL,
              extratags HSTORE,
              geometry GEOMETRY(Point, 4326) NOT NULL
              );
            CREATE UNIQUE INDEX place_entrance_osm_id_idx ON place_entrance
              USING BTREE (osm_id);
              """)


@_migration(5, 2, 99, 1)
def convert_country_tokens(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Convert country word tokens

        Country tokens now save the country in the info field instead of the
        word. This migration removes all country tokens from the word table
        and reimports the default country name. This means that custom names
        are lost. If you need them back, invalidate the OSM objects containing
        the names by setting indexed_status to 2 and then reindex the database.
    """
    tokenizer = tokenizer_factory.get_tokenizer_for_db(config)
    # There is only one tokenizer at the time of migration, so we make
    # some assumptions here about the structure of the database. This will
    # fail if somebody has written a custom tokenizer.
    with conn.cursor() as cur:
        cur.execute("DELETE FROM word WHERE type = 'C'")
    conn.commit()

    setup_country_config(config)
    create_country_names(conn, tokenizer, config.get_str_list('LANGUAGES'))


@_migration(5, 2, 99, 2)
def create_place_postcode_table(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Restructure postcode tables
    """
    sqlp = SQLPreprocessor(conn, config)
    mutable = not is_frozen(conn)
    has_place_table = table_exists(conn, 'place_postcode')
    has_postcode_table = table_exists(conn, 'location_postcodes')
    if mutable and not has_place_table:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE place_postcode (
                    osm_type CHAR(1) NOT NULL,
                    osm_id BIGINT NOT NULL,
                    postcode TEXT NOT NULL,
                    country_code TEXT,
                    centroid GEOMETRY(Point, 4326) NOT NULL,
                    geometry GEOMETRY(Geometry, 4326)
                )
                """)
            # Move postcode points into the new table
            cur.execute("ALTER TABLE place DISABLE TRIGGER ALL")
            cur.execute(
                """
                WITH deleted AS (
                  DELETE FROM place
                  WHERE (class = 'place' AND type = 'postcode')
                        OR (osm_type = 'R'
                            AND class = 'boundary' AND type = 'postal_code')
                  RETURNING osm_type, osm_id, address->'postcode' as postcode,
                            ST_Centroid(geometry) as centroid,
                            (CASE WHEN class = 'place' THEN NULL ELSE geometry END) as geometry)
                INSERT INTO place_postcode (osm_type, osm_id, postcode, centroid, geometry)
                    (SELECT * FROM deleted
                     WHERE deleted.postcode is not NULL AND deleted.centroid is not NULL)
                """)
            cur.execute(
                """
                CREATE INDEX place_postcode_osm_id_idx ON place_postcode
                  USING BTREE (osm_type, osm_id)
                """)
            cur.execute(
                """
                CREATE INDEX place_postcode_postcode_idx ON place_postcode
                  USING BTREE (postcode)
                """)
            cur.execute("ALTER TABLE place ENABLE TRIGGER ALL")
    if not has_postcode_table:
        sqlp.run_sql_file(conn, 'functions/postcode_triggers.sql')
        with conn.cursor() as cur:
            # create a new location_postcode table which will replace the
            # old one atomically in the end
            cur.execute(
                """
                CREATE TABLE location_postcodes (
                    place_id BIGINT,
                    osm_id BIGINT,
                    rank_search SMALLINT,
                    parent_place_id BIGINT,
                    indexed_status SMALLINT,
                    indexed_date TIMESTAMP,
                    country_code VARCHAR(2),
                    postcode TEXT,
                    centroid Geometry(Point, 4326),
                    geometry Geometry(Geometry, 4326) NOT NULL
                )
                """)
            sqlp.run_string(conn,
                            'GRANT SELECT ON location_postcodes TO "{{config.DATABASE_WEBUSER}}"')
            # remove postcodes from the various auxillary tables
            cur.execute(
                """
                DELETE FROM place_addressline
                  WHERE address_place_id = ANY(
                    SELECT place_id FROM placex
                      WHERE osm_type = 'R'
                            AND class = 'boundary' AND type = 'postal_code')
                """)
            if mutable:
                cur.execute(
                    """
                    SELECT deleteLocationArea(partition, place_id, rank_search),
                           deleteSearchName(partition, place_id)
                      FROM placex
                      WHERE osm_type = 'R' AND class = 'boundary' AND type = 'postal_code'
                    """)
            if table_exists(conn, 'search_name'):
                cur.execute(
                    """
                    DELETE FROM search_name
                      WHERE place_id = ANY(
                        SELECT place_id FROM placex
                          WHERE osm_type = 'R'
                                AND class = 'boundary' AND type = 'postal_code')
                    """)
            # move postcode areas from placex to location_postcodes
            # avoiding automatic invalidation
            cur.execute("ALTER TABLE placex DISABLE TRIGGER ALL")
            cur.execute(
                """
                WITH deleted AS (
                    DELETE FROM placex
                      WHERE osm_type = 'R'
                            AND class = 'boundary' AND type = 'postal_code'
                      RETURNING place_id, osm_id, rank_search, parent_place_id,
                                indexed_status, indexed_date,
                                country_code, postcode, centroid, geometry)
                INSERT INTO location_postcodes (SELECT * from deleted)
                """)
            cur.execute("ALTER TABLE placex ENABLE TRIGGER ALL")
            # remove any old postcode centroid that would overlap with areas
            cur.execute(
                """
                DELETE FROM location_postcode o USING location_postcodes n
                   WHERE o.country_code = n.country_code
                         AND o.postcode = n.postcode
                """)
            # copy over old postcodes
            cur.execute(
                """
                INSERT INTO location_postcodes
                    (SELECT place_id, NULL, rank_search, parent_place_id,
                            indexed_status, indexed_date, country_code,
                            postcode, geometry,
                            ST_Expand(geometry, 0.05)
                     FROM location_postcode)
                """)
            # add indexes and triggers
            cur.execute("""CREATE INDEX idx_location_postcodes_geometry
                           ON location_postcodes USING GIST(geometry)""")
            cur.execute("""CREATE INDEX idx_location_postcodes_id
                           ON location_postcodes USING BTREE(place_id)""")
            cur.execute("""CREATE INDEX idx_location_postcodes_osmid
                           ON location_postcodes USING BTREE(osm_id)""")
            cur.execute("""CREATE INDEX idx_location_postcodes_postcode
                           ON location_postcodes USING BTREE(postcode, country_code)""")
            cur.execute("""CREATE INDEX idx_location_postcodes_parent_place_id
                           ON location_postcodes USING BTREE(parent_place_id)""")
            cur.execute("""CREATE TRIGGER location_postcodes_before_update
                           BEFORE UPDATE ON location_postcodes
                           FOR EACH ROW EXECUTE PROCEDURE postcodes_update()""")
            cur.execute("""CREATE TRIGGER location_postcodes_before_delete
                           BEFORE DELETE ON location_postcodes
                           FOR EACH ROW EXECUTE PROCEDURE postcodes_delete()""")
            cur.execute("""CREATE TRIGGER location_postcodes_before_insert
                           BEFORE INSERT ON location_postcodes
                           FOR EACH ROW EXECUTE PROCEDURE postcodes_insert()""")
        sqlp.run_string(
            conn,
            """
            CREATE INDEX IF NOT EXISTS idx_placex_geometry_reverse_lookupPolygon_nopostcode
            ON placex USING gist (geometry) {{db.tablespace.search_index}}
            WHERE St_GeometryType(geometry) in ('ST_Polygon', 'ST_MultiPolygon')
            AND rank_address between 4 and 25
            AND name is not null AND linked_place_id is null;

            CREATE INDEX IF NOT EXISTS idx_placex_geometry_reverse_lookupPlaceNode_nopostcode
              ON placex USING gist (ST_Buffer(geometry, reverse_place_diameter(rank_search)))
              {{db.tablespace.search_index}}
              WHERE rank_address between 4 and 25
                AND name is not null AND linked_place_id is null AND osm_type = 'N';

            CREATE INDEX idx_placex_geometry_placenode_nopostcode ON placex
              USING SPGIST (geometry) {{db.tablespace.address_index}}
              WHERE osm_type = 'N' and rank_search < 26 and class = 'place';
            ANALYSE;
            """)
