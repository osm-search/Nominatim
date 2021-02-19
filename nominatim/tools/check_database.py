"""
Collection of functions that check if the database is complete and functional.
"""
from enum import Enum
from textwrap import dedent

import psycopg2

from ..db.connection import connect
from ..errors import UsageError

CHECKLIST = []

class CheckState(Enum):
    """ Possible states of a check. FATAL stops check execution entirely.
    """
    OK = 0
    FAIL = 1
    FATAL = 2
    NOT_APPLICABLE = 3

def _check(hint=None):
    """ Decorator for checks. It adds the function to the list of
        checks to execute and adds the code for printing progress messages.
    """
    def decorator(func):
        title = func.__doc__.split('\n', 1)[0].strip()
        def run_check(conn, config):
            print(title, end=' ... ')
            ret = func(conn, config)
            if isinstance(ret, tuple):
                ret, params = ret
            else:
                params = {}
            if ret == CheckState.OK:
                print('\033[92mOK\033[0m')
            elif ret == CheckState.NOT_APPLICABLE:
                print('not applicable')
            else:
                print('\x1B[31mFailed\033[0m')
                if hint:
                    print(dedent(hint.format(**params)))
            return ret

        CHECKLIST.append(run_check)
        return run_check

    return decorator

class _BadConnection: # pylint: disable=R0903

    def __init__(self, msg):
        self.msg = msg

    def close(self):
        """ Dummy function to provide the implementation.
        """

def check_database(config):
    """ Run a number of checks on the database and return the status.
    """
    try:
        conn = connect(config.get_libpq_dsn())
    except UsageError as err:
        conn = _BadConnection(str(err))

    overall_result = 0
    for check in CHECKLIST:
        ret = check(conn, config)
        if ret == CheckState.FATAL:
            conn.close()
            return 1
        if ret in (CheckState.FATAL, CheckState.FAIL):
            overall_result = 1

    conn.close()
    return overall_result


def _get_indexes(conn):
    indexes = ['idx_word_word_id',
               'idx_place_addressline_address_place_id',
               'idx_placex_rank_search',
               'idx_placex_rank_address',
               'idx_placex_parent_place_id',
               'idx_placex_geometry_reverse_lookuppolygon',
               'idx_placex_geometry_reverse_placenode',
               'idx_osmline_parent_place_id',
               'idx_osmline_parent_osm_id',
               'idx_postcode_id',
               'idx_postcode_postcode'
              ]
    if conn.table_exists('search_name'):
        indexes.extend(('idx_search_name_nameaddress_vector',
                        'idx_search_name_name_vector',
                        'idx_search_name_centroid'))
    if conn.table_exists('place'):
        indexes.extend(('idx_placex_pendingsector',
                        'idx_location_area_country_place_id',
                        'idx_place_osm_unique'
                       ))

    return indexes


### CHECK FUNCTIONS
#
# Functions are exectured in the order they appear here.

@_check(hint="""\
             {error}

             Hints:
             * Is the database server started?
             * Check the NOMINATIM_DATABASE_DSN variable in your local .env
             * Try connecting to the database with the same settings

             Project directory: {config.project_dir}
             Current setting of NOMINATIM_DATABASE_DSN: {config.DATABASE_DSN}
             """)
def check_connection(conn, config):
    """ Checking database connection
    """
    if isinstance(conn, _BadConnection):
        return CheckState.FATAL, dict(error=conn.msg, config=config)

    return CheckState.OK

@_check(hint="""\
             placex table not found

             Hints:
             * Are you connecting to the right database?
             * Did the import process finish without errors?

             Project directory: {config.project_dir}
             Current setting of NOMINATIM_DATABASE_DSN: {config.DATABASE_DSN}
             """)
def check_placex_table(conn, config):
    """ Checking for placex table
    """
    if conn.table_exists('placex'):
        return CheckState.OK

    return CheckState.FATAL, dict(config=config)


@_check(hint="""placex table has no data. Did the import finish sucessfully?""")
def check_placex_size(conn, config): # pylint: disable=W0613
    """ Checking for placex content
    """
    with conn.cursor() as cur:
        cnt = cur.scalar('SELECT count(*) FROM (SELECT * FROM placex LIMIT 100) x')

    return CheckState.OK if cnt > 0 else CheckState.FATAL


@_check(hint="""\
             The Postgresql extension nominatim.so was not correctly loaded.

             Error: {error}

             Hints:
             * Check the output of the CMmake/make installation step
             * Does nominatim.so exist?
             * Does nominatim.so exist on the database server?
             * Can nominatim.so be accessed by the database user?
             """)
def check_module(conn, config): # pylint: disable=W0613
    """ Checking that nominatim.so module is installed
    """
    with conn.cursor() as cur:
        try:
            out = cur.scalar("SELECT make_standard_name('a')")
        except psycopg2.ProgrammingError as err:
            return CheckState.FAIL, dict(error=str(err))

        if out != 'a':
            return CheckState.FAIL, dict(error='Unexpected result for make_standard_name()')

        return CheckState.OK


@_check(hint="""\
             The indexing didn't finish. {count} entries are not yet indexed.

             To index the remaining entries, run:   {index_cmd}
             """)
def check_indexing(conn, config): # pylint: disable=W0613
    """ Checking indexing status
    """
    with conn.cursor() as cur:
        cnt = cur.scalar('SELECT count(*) FROM placex WHERE indexed_status > 0')

    if cnt == 0:
        return CheckState.OK

    if conn.index_exists('idx_word_word_id'):
        # Likely just an interrupted update.
        index_cmd = 'nominatim index'
    else:
        # Looks like the import process got interrupted.
        index_cmd = 'nominatim import --continue indexing'

    return CheckState.FAIL, dict(count=cnt, index_cmd=index_cmd)


@_check(hint="""\
             The following indexes are missing:
               {indexes}

             Rerun the index creation with:   nominatim import --continue db-postprocess
             """)
def check_database_indexes(conn, config): # pylint: disable=W0613
    """ Checking that database indexes are complete
    """
    missing = []
    for index in _get_indexes(conn):
        if not conn.index_exists(index):
            missing.append(index)

    if missing:
        return CheckState.FAIL, dict(indexes='\n  '.join(missing))

    return CheckState.OK


@_check(hint="""\
             At least one index is invalid. That can happen, e.g. when index creation was
             disrupted and later restarted. You should delete the affected indices
             and recreate them.

             Invalid indexes:
               {indexes}
             """)
def check_database_index_valid(conn, config): # pylint: disable=W0613
    """ Checking that all database indexes are valid
    """
    with conn.cursor() as cur:
        cur.execute(""" SELECT relname FROM pg_class, pg_index
                        WHERE pg_index.indisvalid = false
                        AND pg_index.indexrelid = pg_class.oid""")

        broken = list(cur)

    if broken:
        return CheckState.FAIL, dict(indexes='\n  '.join(broken))

    return CheckState.OK


@_check(hint="""\
             {error}
             Run TIGER import again:   nominatim add-data --tiger-data <DIR>
             """)
def check_tiger_table(conn, config):
    """ Checking TIGER external data table.
    """
    if not config.get_bool('USE_US_TIGER_DATA'):
        return CheckState.NOT_APPLICABLE

    if not conn.table_exists('location_property_tiger'):
        return CheckState.FAIL, dict(error='TIGER data table not found.')

    with conn.cursor() as cur:
        if cur.scalar('SELECT count(*) FROM location_property_tiger') == 0:
            return CheckState.FAIL, dict(error='TIGER data table is empty.')

    return CheckState.OK
