# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for database migration to newer software versions.
"""
from typing import List, Tuple, Callable, Any
import logging

from psycopg2 import sql as pysql

from nominatim.config import Configuration
from nominatim.db import properties
from nominatim.db.connection import connect, Connection
from nominatim.version import NOMINATIM_VERSION, version_str
from nominatim.tools import refresh
from nominatim.tokenizer import factory as tokenizer_factory
from nominatim.errors import UsageError

LOG = logging.getLogger()

VersionTuple = Tuple[int, int, int, int]

_MIGRATION_FUNCTIONS : List[Tuple[VersionTuple, Callable[..., None]]] = []

def migrate(config: Configuration, paths: Any) -> int:
    """ Check for the current database version and execute migrations,
        if necesssary.
    """
    with connect(config.get_libpq_dsn()) as conn:
        if conn.table_exists('nominatim_properties'):
            db_version_str = properties.get_property(conn, 'database_version')
        else:
            db_version_str = None

        if db_version_str is not None:
            parts = db_version_str.split('.')
            db_version = tuple(int(x) for x in parts[:2] + parts[2].split('-'))

            if db_version == NOMINATIM_VERSION:
                LOG.warning("Database already at latest version (%s)", db_version_str)
                return 0

            LOG.info("Detected database version: %s", db_version_str)
        else:
            db_version = _guess_version(conn)


        has_run_migration = False
        for version, func in _MIGRATION_FUNCTIONS:
            if db_version <= version:
                title = func.__doc__ or ''
                LOG.warning("Running: %s (%s)", title.split('\n', 1)[0],
                            version_str(version))
                kwargs = dict(conn=conn, config=config, paths=paths)
                func(**kwargs)
                conn.commit()
                has_run_migration = True

        if has_run_migration:
            LOG.warning('Updating SQL functions.')
            refresh.create_functions(conn, config)
            tokenizer = tokenizer_factory.get_tokenizer_for_db(config)
            tokenizer.update_sql_functions(config)

        properties.set_property(conn, 'database_version', version_str())

        conn.commit()

    return 0


def _guess_version(conn: Connection) -> VersionTuple:
    """ Guess a database version when there is no property table yet.
        Only migrations for 3.6 and later are supported, so bail out
        when the version seems older.
    """
    with conn.cursor() as cur:
        # In version 3.6, the country_name table was updated. Check for that.
        cnt = cur.scalar("""SELECT count(*) FROM
                            (SELECT svals(name) FROM  country_name
                             WHERE country_code = 'gb')x;
                         """)
        if cnt < 100:
            LOG.fatal('It looks like your database was imported with a version '
                      'prior to 3.6.0. Automatic migration not possible.')
            raise UsageError('Migration not possible.')

    return (3, 5, 0, 99)



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
        _MIGRATION_FUNCTIONS.append(((major, minor, patch, dbpatch), func))
        return func

    return decorator


@_migration(3, 5, 0, 99)
def import_status_timestamp_change(conn: Connection, **_: Any) -> None:
    """ Add timezone to timestamp in status table.

        The import_status table has been changed to include timezone information
        with the time stamp.
    """
    with conn.cursor() as cur:
        cur.execute("""ALTER TABLE import_status ALTER COLUMN lastimportdate
                       TYPE timestamp with time zone;""")


@_migration(3, 5, 0, 99)
def add_nominatim_property_table(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Add nominatim_property table.
    """
    if not conn.table_exists('nominatim_properties'):
        with conn.cursor() as cur:
            cur.execute(pysql.SQL("""CREATE TABLE nominatim_properties (
                                        property TEXT,
                                        value TEXT);
                                     GRANT SELECT ON TABLE nominatim_properties TO {};
                                  """).format(pysql.Identifier(config.DATABASE_WEBUSER)))

@_migration(3, 6, 0, 0)
def change_housenumber_transliteration(conn: Connection, **_: Any) -> None:
    """ Transliterate housenumbers.

        The database schema switched from saving raw housenumbers in
        placex.housenumber to saving transliterated ones.

        Note: the function create_housenumber_id() has been dropped in later
              versions.
    """
    with conn.cursor() as cur:
        cur.execute("""CREATE OR REPLACE FUNCTION create_housenumber_id(housenumber TEXT)
                       RETURNS TEXT AS $$
                       DECLARE
                         normtext TEXT;
                       BEGIN
                         SELECT array_to_string(array_agg(trans), ';')
                           INTO normtext
                           FROM (SELECT lookup_word as trans,
                                        getorcreate_housenumber_id(lookup_word)
                                 FROM (SELECT make_standard_name(h) as lookup_word
                                       FROM regexp_split_to_table(housenumber, '[,;]') h) x) y;
                         return normtext;
                       END;
                       $$ LANGUAGE plpgsql STABLE STRICT;""")
        cur.execute("DELETE FROM word WHERE class = 'place' and type = 'house'")
        cur.execute("""UPDATE placex
                       SET housenumber = create_housenumber_id(housenumber)
                       WHERE housenumber is not null""")


@_migration(3, 7, 0, 0)
def switch_placenode_geometry_index(conn: Connection, **_: Any) -> None:
    """ Replace idx_placex_geometry_reverse_placeNode index.

        Make the index slightly more permissive, so that it can also be used
        when matching up boundaries and place nodes. It makes the index
        idx_placex_adminname index unnecessary.
    """
    with conn.cursor() as cur:
        cur.execute(""" CREATE INDEX IF NOT EXISTS idx_placex_geometry_placenode ON placex
                        USING GIST (geometry)
                        WHERE osm_type = 'N' and rank_search < 26
                              and class = 'place' and type != 'postcode'
                              and linked_place_id is null""")
        cur.execute(""" DROP INDEX IF EXISTS idx_placex_adminname """)


@_migration(3, 7, 0, 1)
def install_legacy_tokenizer(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Setup legacy tokenizer.

        If no other tokenizer has been configured yet, then create the
        configuration for the backwards-compatible legacy tokenizer
    """
    if properties.get_property(conn, 'tokenizer') is None:
        with conn.cursor() as cur:
            for table in ('placex', 'location_property_osmline'):
                has_column = cur.scalar("""SELECT count(*) FROM information_schema.columns
                                           WHERE table_name = %s
                                           and column_name = 'token_info'""",
                                        (table, ))
                if has_column == 0:
                    cur.execute(pysql.SQL('ALTER TABLE {} ADD COLUMN token_info JSONB')
                                .format(pysql.Identifier(table)))
        tokenizer = tokenizer_factory.create_tokenizer(config, init_db=False,
                                                       module_name='legacy')

        tokenizer.migrate_database(config) # type: ignore[attr-defined]


@_migration(4, 0, 99, 0)
def create_tiger_housenumber_index(conn: Connection, **_: Any) -> None:
    """ Create idx_location_property_tiger_parent_place_id with included
        house number.

        The inclusion is needed for efficient lookup of housenumbers in
        full address searches.
    """
    if conn.server_version_tuple() >= (11, 0, 0):
        with conn.cursor() as cur:
            cur.execute(""" CREATE INDEX IF NOT EXISTS
                                idx_location_property_tiger_housenumber_migrated
                            ON location_property_tiger
                            USING btree(parent_place_id)
                            INCLUDE (startnumber, endnumber) """)


@_migration(4, 0, 99, 1)
def create_interpolation_index_on_place(conn: Connection, **_: Any) -> None:
    """ Create idx_place_interpolations for lookup of interpolation lines
        on updates.
    """
    with conn.cursor() as cur:
        cur.execute("""CREATE INDEX IF NOT EXISTS idx_place_interpolations
                       ON place USING gist(geometry)
                       WHERE osm_type = 'W' and address ? 'interpolation'""")


@_migration(4, 0, 99, 2)
def add_step_column_for_interpolation(conn: Connection, **_: Any) -> None:
    """ Add a new column 'step' to the interpolations table.

        Also converts the data into the stricter format which requires that
        startnumbers comply with the odd/even requirements.
    """
    if conn.table_has_column('location_property_osmline', 'step'):
        return

    with conn.cursor() as cur:
        # Mark invalid all interpolations with no intermediate numbers.
        cur.execute("""UPDATE location_property_osmline SET startnumber = null
                       WHERE endnumber - startnumber <= 1 """)
        # Align the start numbers where odd/even does not match.
        cur.execute("""UPDATE location_property_osmline
                       SET startnumber = startnumber + 1,
                           linegeo = ST_LineSubString(linegeo,
                                                      1.0 / (endnumber - startnumber)::float,
                                                      1)
                       WHERE (interpolationtype = 'odd' and startnumber % 2 = 0)
                              or (interpolationtype = 'even' and startnumber % 2 = 1)
                    """)
        # Mark invalid odd/even interpolations with no intermediate numbers.
        cur.execute("""UPDATE location_property_osmline SET startnumber = null
                       WHERE interpolationtype in ('odd', 'even')
                             and endnumber - startnumber = 2""")
        # Finally add the new column and populate it.
        cur.execute("ALTER TABLE location_property_osmline ADD COLUMN step SMALLINT")
        cur.execute("""UPDATE location_property_osmline
                         SET step = CASE WHEN interpolationtype = 'all'
                                         THEN 1 ELSE 2 END
                    """)


@_migration(4, 0, 99, 3)
def add_step_column_for_tiger(conn: Connection, **_: Any) -> None:
    """ Add a new column 'step' to the tiger data table.
    """
    if conn.table_has_column('location_property_tiger', 'step'):
        return

    with conn.cursor() as cur:
        cur.execute("ALTER TABLE location_property_tiger ADD COLUMN step SMALLINT")
        cur.execute("""UPDATE location_property_tiger
                         SET step = CASE WHEN interpolationtype = 'all'
                                         THEN 1 ELSE 2 END
                    """)


@_migration(4, 0, 99, 4)
def add_derived_name_column_for_country_names(conn: Connection, **_: Any) -> None:
    """ Add a new column 'derived_name' which in the future takes the
        country names as imported from OSM data.
    """
    if not conn.table_has_column('country_name', 'derived_name'):
        with conn.cursor() as cur:
            cur.execute("ALTER TABLE country_name ADD COLUMN derived_name public.HSTORE")


@_migration(4, 0, 99, 5)
def mark_internal_country_names(conn: Connection, config: Configuration, **_: Any) -> None:
    """ Names from the country table should be marked as internal to prevent
        them from being deleted. Only necessary for ICU tokenizer.
    """
    import psycopg2.extras # pylint: disable=import-outside-toplevel

    tokenizer = tokenizer_factory.get_tokenizer_for_db(config)
    with tokenizer.name_analyzer() as analyzer:
        with conn.cursor() as cur:
            psycopg2.extras.register_hstore(cur)
            cur.execute("SELECT country_code, name FROM country_name")

            for country_code, names in cur:
                if not names:
                    names = {}
                names['countrycode'] = country_code
                analyzer.add_country_names(country_code, names)
