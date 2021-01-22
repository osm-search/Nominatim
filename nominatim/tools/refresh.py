"""
Functions for bringing auxiliary data in the database up-to-date.
"""
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
