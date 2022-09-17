# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Collection of functions that check if the database is complete and functional.
"""
from typing import Callable, Optional, Any, Union, Tuple, Mapping, List
from enum import Enum
from textwrap import dedent

from nominatim.config import Configuration
from nominatim.db.connection import connect, Connection
from nominatim.errors import UsageError
from nominatim.tokenizer import factory as tokenizer_factory

CHECKLIST = []

class CheckState(Enum):
    """ Possible states of a check. FATAL stops check execution entirely.
    """
    OK = 0
    FAIL = 1
    FATAL = 2
    NOT_APPLICABLE = 3
    WARN = 4

CheckResult = Union[CheckState, Tuple[CheckState, Mapping[str, Any]]]
CheckFunc = Callable[[Connection, Configuration], CheckResult]

def _check(hint: Optional[str] = None) -> Callable[[CheckFunc], CheckFunc]:
    """ Decorator for checks. It adds the function to the list of
        checks to execute and adds the code for printing progress messages.
    """
    def decorator(func: CheckFunc) -> CheckFunc:
        title = (func.__doc__ or '').split('\n', 1)[0].strip()

        def run_check(conn: Connection, config: Configuration) -> CheckState:
            print(title, end=' ... ')
            ret = func(conn, config)
            if isinstance(ret, tuple):
                ret, params = ret
            else:
                params = {}
            if ret == CheckState.OK:
                print('\033[92mOK\033[0m')
            elif ret == CheckState.WARN:
                print('\033[93mWARNING\033[0m')
                if hint:
                    print('')
                    print(dedent(hint.format(**params)))
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

class _BadConnection:

    def __init__(self, msg: str) -> None:
        self.msg = msg

    def close(self) -> None:
        """ Dummy function to provide the implementation.
        """

def check_database(config: Configuration) -> int:
    """ Run a number of checks on the database and return the status.
    """
    try:
        conn = connect(config.get_libpq_dsn()).connection
    except UsageError as err:
        conn = _BadConnection(str(err)) # type: ignore[assignment]

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


def _get_indexes(conn: Connection) -> List[str]:
    indexes = ['idx_place_addressline_address_place_id',
               'idx_placex_rank_search',
               'idx_placex_rank_address',
               'idx_placex_parent_place_id',
               'idx_placex_geometry_reverse_lookuppolygon',
               'idx_placex_geometry_placenode',
               'idx_osmline_parent_place_id',
               'idx_osmline_parent_osm_id',
               'idx_postcode_id',
               'idx_postcode_postcode'
              ]
    if conn.table_exists('search_name'):
        indexes.extend(('idx_search_name_nameaddress_vector',
                        'idx_search_name_name_vector',
                        'idx_search_name_centroid'))
        if conn.server_version_tuple() >= (11, 0, 0):
            indexes.extend(('idx_placex_housenumber',
                            'idx_osmline_parent_osm_id_with_hnr'))
    if conn.table_exists('place'):
        indexes.extend(('idx_placex_pendingsector',
                        'idx_location_area_country_place_id',
                        'idx_place_osm_unique'))

    return indexes


# CHECK FUNCTIONS
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
def check_connection(conn: Any, config: Configuration) -> CheckResult:
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
def check_placex_table(conn: Connection, config: Configuration) -> CheckResult:
    """ Checking for placex table
    """
    if conn.table_exists('placex'):
        return CheckState.OK

    return CheckState.FATAL, dict(config=config)


@_check(hint="""placex table has no data. Did the import finish successfully?""")
def check_placex_size(conn: Connection, _: Configuration) -> CheckResult:
    """ Checking for placex content
    """
    with conn.cursor() as cur:
        cnt = cur.scalar('SELECT count(*) FROM (SELECT * FROM placex LIMIT 100) x')

    return CheckState.OK if cnt > 0 else CheckState.FATAL


@_check(hint="""{msg}""")
def check_tokenizer(_: Connection, config: Configuration) -> CheckResult:
    """ Checking that tokenizer works
    """
    try:
        tokenizer = tokenizer_factory.get_tokenizer_for_db(config)
    except UsageError:
        return CheckState.FAIL, dict(msg="""\
            Cannot load tokenizer. Did the import finish successfully?""")

    result = tokenizer.check_database(config)

    if result is None:
        return CheckState.OK

    return CheckState.FAIL, dict(msg=result)


@_check(hint="""\
             Wikipedia/Wikidata importance tables missing.
             Quality of search results may be degraded. Reverse geocoding is unaffected.
             See https://nominatim.org/release-docs/latest/admin/Import/#wikipediawikidata-rankings
             """)
def check_existance_wikipedia(conn: Connection, _: Configuration) -> CheckResult:
    """ Checking for wikipedia/wikidata data
    """
    if not conn.table_exists('search_name'):
        return CheckState.NOT_APPLICABLE

    with conn.cursor() as cur:
        cnt = cur.scalar('SELECT count(*) FROM wikipedia_article')

        return CheckState.WARN if cnt == 0 else CheckState.OK


@_check(hint="""\
             The indexing didn't finish. {count} entries are not yet indexed.

             To index the remaining entries, run:   {index_cmd}
             """)
def check_indexing(conn: Connection, _: Configuration) -> CheckResult:
    """ Checking indexing status
    """
    with conn.cursor() as cur:
        cnt = cur.scalar('SELECT count(*) FROM placex WHERE indexed_status > 0')

    if cnt == 0:
        return CheckState.OK

    if conn.index_exists('idx_placex_rank_search'):
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
def check_database_indexes(conn: Connection, _: Configuration) -> CheckResult:
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
def check_database_index_valid(conn: Connection, _: Configuration) -> CheckResult:
    """ Checking that all database indexes are valid
    """
    with conn.cursor() as cur:
        cur.execute(""" SELECT relname FROM pg_class, pg_index
                        WHERE pg_index.indisvalid = false
                        AND pg_index.indexrelid = pg_class.oid""")

        broken = [c[0] for c in cur]

    if broken:
        return CheckState.FAIL, dict(indexes='\n  '.join(broken))

    return CheckState.OK


@_check(hint="""\
             {error}
             Run TIGER import again:   nominatim add-data --tiger-data <DIR>
             """)
def check_tiger_table(conn: Connection, config: Configuration) -> CheckResult:
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
