"""
Functions for bringing auxiliary data in the database up-to-date.
"""
import json

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
