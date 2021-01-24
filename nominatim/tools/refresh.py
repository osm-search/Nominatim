"""
Functions for bringing auxiliary data in the database up-to-date.
"""
import json
import re

from psycopg2.extras import execute_values

from ..db.utils import execute_file

def update_postcodes(conn, datadir):
    """ Recalculate postcode centroids and add, remove and update entries in the
        location_postcode table. `conn` is an opne connection to the database.
    """
    execute_file(conn, datadir / 'sql' / 'update-postcodes.sql')


def recompute_word_counts(conn, datadir):
    """ Compute the frequency of full-word search terms.
    """
    execute_file(conn, datadir / 'sql' / 'words_from_search_name.sql')


def _add_address_level_rows_from_entry(rows, entry):
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

def load_address_levels(conn, table, levels):
    """ Replace the `address_levels` table with the contents of `levels'.

        A new table is created any previously existing table is dropped.
        The table has the following columns:
            country, class, type, rank_search, rank_address
    """
    rows = []
    for entry in levels:
        _add_address_level_rows_from_entry(rows, entry)

    with conn.cursor() as cur:
        cur.execute('DROP TABLE IF EXISTS {}'.format(table))

        cur.execute("""CREATE TABLE {} (country_code varchar(2),
                                        class TEXT,
                                        type TEXT,
                                        rank_search SMALLINT,
                                        rank_address SMALLINT)""".format(table))

        execute_values(cur, "INSERT INTO {} VALUES %s".format(table), rows)

        cur.execute('CREATE UNIQUE INDEX ON {} (country_code, class, type)'.format(table))

    conn.commit()

def load_address_levels_from_file(conn, config_file):
    """ Replace the `address_levels` table with the contents of the config
        file.
    """
    with config_file.open('r') as fdesc:
        load_address_levels(conn, 'address_levels', json.load(fdesc))

PLPGSQL_BASE_MODULES = (
    'utils.sql',
    'normalization.sql',
    'ranking.sql',
    'importance.sql',
    'address_lookup.sql',
    'interpolation.sql'
)

PLPGSQL_TABLE_MODULES = (
    ('place', 'place_triggers.sql'),
    ('placex', 'placex_triggers.sql'),
    ('location_postcode', 'postcode_triggers.sql')
)

def _get_standard_function_sql(conn, config, sql_dir, enable_diff_updates, enable_debug):
    """ Read all applicable SQLs containing PL/pgSQL functions, replace
        placefolders and execute them.
    """
    sql_func_dir = sql_dir / 'functions'
    sql = ''

    # Get the basic set of functions that is always imported.
    for sql_file in PLPGSQL_BASE_MODULES:
        with (sql_func_dir / sql_file).open('r') as fdesc:
            sql += fdesc.read()

    # Some files require the presence of a certain table
    for table, fname in PLPGSQL_TABLE_MODULES:
        if conn.table_exists(table):
            with (sql_func_dir / fname).open('r') as fdesc:
                sql += fdesc.read()

    # Replace placeholders.
    sql = sql.replace('{modulepath}',
                      config.DATABASE_MODULE_PATH or str((config.project_dir / 'module').resolve()))

    if enable_diff_updates:
        sql = sql.replace('RETURN NEW; -- %DIFFUPDATES%', '--')

    if enable_debug:
        sql = sql.replace('--DEBUG:', '')

    if config.get_bool('LIMIT_REINDEXING'):
        sql = sql.replace('--LIMIT INDEXING:', '')

    if not config.get_bool('USE_US_TIGER_DATA'):
        sql = sql.replace('-- %NOTIGERDATA% ', '')

    if not config.get_bool('USE_AUX_LOCATION_DATA'):
        sql = sql.replace('-- %NOAUXDATA% ', '')

    reverse_only = 'false' if conn.table_exists('search_name') else 'true'

    return sql.replace('%REVERSE-ONLY%', reverse_only)


def replace_partition_string(sql, partitions):
    """ Replace a partition template with the actual partition code.
    """
    for match in re.findall('^-- start(.*?)^-- end', sql, re.M | re.S):
        repl = ''
        for part in partitions:
            repl += match.replace('-partition-', str(part))
        sql = sql.replace(match, repl)

    return sql

def _get_partition_function_sql(conn, sql_dir):
    """ Create functions that work on partition tables.
    """
    with conn.cursor() as cur:
        cur.execute('SELECT distinct partition FROM country_name')
        partitions = set([0])
        for row in cur:
            partitions.add(row[0])

    with (sql_dir / 'partition-functions.src.sql').open('r') as fdesc:
        sql = fdesc.read()

    return replace_partition_string(sql, sorted(partitions))

def create_functions(conn, config, data_dir,
                     enable_diff_updates=True, enable_debug=False):
    """ (Re)create the PL/pgSQL functions.
    """
    sql_dir = data_dir / 'sql'

    sql = _get_standard_function_sql(conn, config, sql_dir,
                                     enable_diff_updates, enable_debug)
    sql += _get_partition_function_sql(conn, sql_dir)

    with conn.cursor() as cur:
        cur.execute(sql)

    conn.commit()
