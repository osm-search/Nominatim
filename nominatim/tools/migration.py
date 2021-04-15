"""
Functions for database migration to newer software versions.
"""
import logging

from ..db import properties
from ..db.connection import connect
from ..version import NOMINATIM_VERSION
from . import refresh, database_import
from ..errors import UsageError

LOG = logging.getLogger()

_MIGRATION_FUNCTIONS = []

def migrate(config, paths):
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
            db_version = tuple([int(x) for x in parts[:2] + parts[2].split('-')])

            if db_version == NOMINATIM_VERSION:
                LOG.warning("Database already at latest version (%s)", db_version_str)
                return 0

            LOG.info("Detected database version: %s", db_version_str)
        else:
            db_version = _guess_version(conn)


        has_run_migration = False
        for version, func in _MIGRATION_FUNCTIONS:
            if db_version <= version:
                LOG.warning("Runnning: %s (%s)", func.__doc__.split('\n', 1)[0],
                            '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(version))
                kwargs = dict(conn=conn, config=config, paths=paths)
                func(**kwargs)
                has_run_migration = True

        if has_run_migration:
            LOG.warning('Updating SQL functions.')
            refresh.create_functions(conn, config, paths.sqllib_dir)

        properties.set_property(conn, 'database_version',
                                '{0[0]}.{0[1]}.{0[2]}-{0[3]}'.format(NOMINATIM_VERSION))

        conn.commit()

    return 0


def _guess_version(conn):
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



def _migration(major, minor, patch=0, dbpatch=0):
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
    def decorator(func):
        _MIGRATION_FUNCTIONS.append(((major, minor, patch, dbpatch), func))

    return decorator


@_migration(3, 5, 0, 99)
def import_status_timestamp_change(conn, **_):
    """ Add timezone to timestamp in status table.

        The import_status table has been changed to include timezone information
        with the time stamp.
    """
    with conn.cursor() as cur:
        cur.execute("""ALTER TABLE import_status ALTER COLUMN lastimportdate
                       TYPE timestamp with time zone;""")


@_migration(3, 5, 0, 99)
def install_database_module_in_project_directory(conn, config, paths, **_):
    """ Install database module in project directory.

        The database module needs to be present in the project directory
        since those were introduced.
    """
    database_import.install_module(paths.module_dir, paths.project_dir,
                                   config.DATABASE_MODULE_PATH, conn=conn)


@_migration(3, 5, 0, 99)
def add_nominatim_property_table(conn, config, **_):
    """ Add nominatim_property table.
    """
    if not conn.table_exists('nominatim_properties'):
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE nominatim_properties (
                               property TEXT,
                               value TEXT);
                           GRANT SELECT ON TABLE nominatim_properties TO "{}";
                        """.format(config.DATABASE_WEBUSER))

@_migration(3, 6, 0, 0)
def change_housenumber_transliteration(conn, **_):
    """ Transliterate housenumbers.

        The database schema switched from saving raw housenumbers in
        placex.housenumber to saving transliterated ones.
    """
    with conn.cursor() as cur:
        cur.execute("""CREATE OR REPLACE FUNCTION create_housenumber_id(housenumber TEXT)
                       RETURNS TEXT AS $$
                       DECLARE
                         normtext TEXT;
                       BEGIN
                         SELECT array_to_string(array_agg(trans), ';')
                           INTO normtext
                           FROM (SELECT lookup_word as trans, getorcreate_housenumber_id(lookup_word)
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
def switch_placenode_geometry_index(conn, **_):
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
