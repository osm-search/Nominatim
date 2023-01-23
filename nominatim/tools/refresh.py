# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for bringing auxiliary data in the database up-to-date.
"""
from typing import MutableSequence, Tuple, Any, Type, Mapping, Sequence, List, cast
import logging
from textwrap import dedent
from pathlib import Path

from psycopg2 import sql as pysql

from nominatim.config import Configuration
from nominatim.db.connection import Connection, connect
from nominatim.db.utils import execute_file
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.version import NOMINATIM_VERSION

LOG = logging.getLogger()

OSM_TYPE = {'N': 'node', 'W': 'way', 'R': 'relation'}

def _add_address_level_rows_from_entry(rows: MutableSequence[Tuple[Any, ...]],
                                       entry: Mapping[str, Any]) -> None:
    """ Converts a single entry from the JSON format for address rank
        descriptions into a flat format suitable for inserting into a
        PostgreSQL table and adds these lines to `rows`.
    """
    countries = entry.get('countries') or (None, )
    for key, values in entry['tags'].items():
        for value, ranks in values.items():
            if isinstance(ranks, list):
                rank_search, rank_address = ranks
            else:
                rank_search = rank_address = ranks
            if not value:
                value = None
            for country in countries:
                rows.append((country, key, value, rank_search, rank_address))


def load_address_levels(conn: Connection, table: str, levels: Sequence[Mapping[str, Any]]) -> None:
    """ Replace the `address_levels` table with the contents of `levels'.

        A new table is created any previously existing table is dropped.
        The table has the following columns:
            country, class, type, rank_search, rank_address
    """
    rows: List[Tuple[Any, ...]]  = []
    for entry in levels:
        _add_address_level_rows_from_entry(rows, entry)

    with conn.cursor() as cur:
        cur.drop_table(table)

        cur.execute(pysql.SQL("""CREATE TABLE {} (
                                        country_code varchar(2),
                                        class TEXT,
                                        type TEXT,
                                        rank_search SMALLINT,
                                        rank_address SMALLINT)
                              """).format(pysql.Identifier(table)))

        cur.execute_values(pysql.SQL("INSERT INTO {} VALUES %s")
                           .format(pysql.Identifier(table)), rows)

        cur.execute(pysql.SQL('CREATE UNIQUE INDEX ON {} (country_code, class, type)')
                    .format(pysql.Identifier(table)))

    conn.commit()


def load_address_levels_from_config(conn: Connection, config: Configuration) -> None:
    """ Replace the `address_levels` table with the content as
        defined in the given configuration. Uses the parameter
        NOMINATIM_ADDRESS_LEVEL_CONFIG to determine the location of the
        configuration file.
    """
    cfg = config.load_sub_configuration('', config='ADDRESS_LEVEL_CONFIG')
    load_address_levels(conn, 'address_levels', cfg)


def create_functions(conn: Connection, config: Configuration,
                     enable_diff_updates: bool = True,
                     enable_debug: bool = False) -> None:
    """ (Re)create the PL/pgSQL functions.
    """
    sql = SQLPreprocessor(conn, config)

    sql.run_sql_file(conn, 'functions.sql',
                     disable_diff_updates=not enable_diff_updates,
                     debug=enable_debug)



WEBSITE_SCRIPTS = (
    'deletable.php',
    'details.php',
    'lookup.php',
    'polygons.php',
    'reverse.php',
    'search.php',
    'status.php'
)

# constants needed by PHP scripts: PHP name, config name, type
PHP_CONST_DEFS = (
    ('Database_DSN', 'DATABASE_DSN', str),
    ('Default_Language', 'DEFAULT_LANGUAGE', str),
    ('Log_DB', 'LOG_DB', bool),
    ('Log_File', 'LOG_FILE', Path),
    ('NoAccessControl', 'CORS_NOACCESSCONTROL', bool),
    ('Places_Max_ID_count', 'LOOKUP_MAX_COUNT', int),
    ('PolygonOutput_MaximumTypes', 'POLYGON_OUTPUT_MAX_TYPES', int),
    ('Search_BatchMode', 'SEARCH_BATCH_MODE', bool),
    ('Search_NameOnlySearchFrequencyThreshold', 'SEARCH_NAME_ONLY_THRESHOLD', str),
    ('Use_US_Tiger_Data', 'USE_US_TIGER_DATA', bool),
    ('MapIcon_URL', 'MAPICON_URL', str),
)


def import_wikipedia_articles(dsn: str, data_path: Path, ignore_errors: bool = False) -> int:
    """ Replaces the wikipedia importance tables with new data.
        The import is run in a single transaction so that the new data
        is replace seamlessly.

        Returns 0 if all was well and 1 if the importance file could not
        be found. Throws an exception if there was an error reading the file.
    """
    datafile = data_path / 'wikimedia-importance.sql.gz'

    if not datafile.exists():
        return 1

    pre_code = """BEGIN;
                  DROP TABLE IF EXISTS "wikipedia_article";
                  DROP TABLE IF EXISTS "wikipedia_redirect"
               """
    post_code = "COMMIT"
    execute_file(dsn, datafile, ignore_errors=ignore_errors,
                 pre_code=pre_code, post_code=post_code)

    return 0

def import_secondary_importance(dsn: str, data_path: Path, ignore_errors: bool = False) -> int:
    """ Replaces the secondary importance raster data table with new data.

        Returns 0 if all was well and 1 if the raster SQL file could not
        be found. Throws an exception if there was an error reading the file.
    """
    datafile = data_path / 'secondary_importance.sql.gz'
    if not datafile.exists():
        return 1

    with connect(dsn) as conn:
        postgis_version = conn.postgis_version_tuple()
        if postgis_version[0] < 3:
            LOG.error('PostGIS version is too old for using OSM raster data.')
            return 2

    execute_file(dsn, datafile, ignore_errors=ignore_errors)

    return 0

def recompute_importance(conn: Connection) -> None:
    """ Recompute wikipedia links and importance for all entries in placex.
        This is a long-running operations that must not be executed in
        parallel with updates.
    """
    with conn.cursor() as cur:
        cur.execute('ALTER TABLE placex DISABLE TRIGGER ALL')
        cur.execute("""
            UPDATE placex SET (wikipedia, importance) =
               (SELECT wikipedia, importance
                FROM compute_importance(extratags, country_code, rank_search, centroid))
            """)
        cur.execute("""
            UPDATE placex s SET wikipedia = d.wikipedia, importance = d.importance
             FROM placex d
             WHERE s.place_id = d.linked_place_id and d.wikipedia is not null
                   and (s.wikipedia is null or s.importance < d.importance);
            """)

        cur.execute('ALTER TABLE placex ENABLE TRIGGER ALL')
    conn.commit()


def _quote_php_variable(var_type: Type[Any], config: Configuration,
                        conf_name: str) -> str:
    if var_type == bool:
        return 'true' if config.get_bool(conf_name) else 'false'

    if var_type == int:
        return cast(str, getattr(config, conf_name))

    if not getattr(config, conf_name):
        return 'false'

    if var_type == Path:
        value = str(config.get_path(conf_name) or '')
    else:
        value = getattr(config, conf_name)

    quoted = value.replace("'", "\\'")
    return f"'{quoted}'"


def setup_website(basedir: Path, config: Configuration, conn: Connection) -> None:
    """ Create the website script stubs.
    """
    if not basedir.exists():
        LOG.info('Creating website directory.')
        basedir.mkdir()

    assert config.project_dir is not None
    template = dedent(f"""\
                      <?php

                      @define('CONST_Debug', $_GET['debug'] ?? false);
                      @define('CONST_LibDir', '{config.lib_dir.php}');
                      @define('CONST_TokenizerDir', '{config.project_dir / 'tokenizer'}');
                      @define('CONST_NominatimVersion', '{NOMINATIM_VERSION!s}');

                      """)

    for php_name, conf_name, var_type in PHP_CONST_DEFS:
        varout = _quote_php_variable(var_type, config, conf_name)

        template += f"@define('CONST_{php_name}', {varout});\n"

    template += f"\nrequire_once('{config.lib_dir.php}/website/{{}}');\n"

    search_name_table_exists = bool(conn and conn.table_exists('search_name'))

    for script in WEBSITE_SCRIPTS:
        if not search_name_table_exists and script == 'search.php':
            (basedir / script).write_text(template.format('reverse-only-search.php'), 'utf-8')
        else:
            (basedir / script).write_text(template.format(script), 'utf-8')


def invalidate_osm_object(osm_type: str, osm_id: int, conn: Connection,
                          recursive: bool = True) -> None:
    """ Mark the given OSM object for reindexing. When 'recursive' is set
        to True (the default), then all dependent objects are marked for
        reindexing as well.

        'osm_type' must be on of 'N' (node), 'W' (way) or 'R' (relation).
        If the given object does not exist, then nothing happens.
    """
    assert osm_type in ('N', 'R', 'W')

    LOG.warning("Invalidating OSM %s %s%s.",
                OSM_TYPE[osm_type], osm_id,
                ' and its dependent places' if recursive else '')

    with conn.cursor() as cur:
        if recursive:
            sql = """SELECT place_force_update(place_id)
                     FROM placex WHERE osm_type = %s and osm_id = %s"""
        else:
            sql = """UPDATE placex SET indexed_status = 2
                     WHERE osm_type = %s and osm_id = %s"""

        cur.execute(sql, (osm_type, osm_id))
