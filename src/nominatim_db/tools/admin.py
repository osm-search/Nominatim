# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for database analysis and maintenance.
"""
from typing import Optional, Tuple, Any, cast
import logging

from psycopg2.extras import Json
from psycopg2 import DataError

from ..typing import DictCursorResult
from ..config import Configuration
from ..db.connection import connect, Cursor, register_hstore
from ..errors import UsageError
from ..tokenizer import factory as tokenizer_factory
from ..data.place_info import PlaceInfo

LOG = logging.getLogger()

def _get_place_info(cursor: Cursor, osm_id: Optional[str],
                    place_id: Optional[int]) -> DictCursorResult:
    sql = """SELECT place_id, extra.*
             FROM placex, LATERAL placex_indexing_prepare(placex) as extra
          """

    values: Tuple[Any, ...]
    if osm_id:
        osm_type = osm_id[0].upper()
        if osm_type not in 'NWR' or not osm_id[1:].isdigit():
            LOG.fatal('OSM ID must be of form <N|W|R><id>. Got: %s', osm_id)
            raise UsageError("OSM ID parameter badly formatted")

        sql += ' WHERE placex.osm_type = %s AND placex.osm_id = %s'
        values = (osm_type, int(osm_id[1:]))
    elif place_id is not None:
        sql += ' WHERE placex.place_id = %s'
        values = (place_id, )
    else:
        LOG.fatal("No OSM object given to index.")
        raise UsageError("OSM object not found")

    cursor.execute(sql + ' LIMIT 1', values)

    if cursor.rowcount < 1:
        LOG.fatal("OSM object %s not found in database.", osm_id)
        raise UsageError("OSM object not found")

    return cast(DictCursorResult, cursor.fetchone())


def analyse_indexing(config: Configuration, osm_id: Optional[str] = None,
                     place_id: Optional[int] = None) -> None:
    """ Analyse indexing of a single Nominatim object.
    """
    with connect(config.get_libpq_dsn()) as conn:
        register_hstore(conn)
        with conn.cursor() as cur:
            place = _get_place_info(cur, osm_id, place_id)

            cur.execute("update placex set indexed_status = 2 where place_id = %s",
                        (place['place_id'], ))

            cur.execute("""SET auto_explain.log_min_duration = '0';
                           SET auto_explain.log_analyze = 'true';
                           SET auto_explain.log_nested_statements = 'true';
                           LOAD 'auto_explain';
                           SET client_min_messages = LOG;
                           SET log_min_messages = FATAL""")

            tokenizer = tokenizer_factory.get_tokenizer_for_db(config)

            with tokenizer.name_analyzer() as analyzer:
                cur.execute("""UPDATE placex
                               SET indexed_status = 0, address = %s, token_info = %s,
                               name = %s, linked_place_id = %s
                               WHERE place_id = %s""",
                            (place['address'],
                             Json(analyzer.process_place(PlaceInfo(place))),
                             place['name'], place['linked_place_id'], place['place_id']))

        # we do not want to keep the results
        conn.rollback()

        for msg in conn.notices:
            print(msg)


def clean_deleted_relations(config: Configuration, age: str) -> None:
    """ Clean deleted relations older than a given age
    """
    with connect(config.get_libpq_dsn()) as conn:
        with conn.cursor() as cur:
            try:
                cur.execute("""SELECT place_force_delete(p.place_id)
                            FROM import_polygon_delete d, placex p
                            WHERE p.osm_type = d.osm_type AND p.osm_id = d.osm_id
                            AND age(p.indexed_date) > %s::interval""",
                            (age, ))
            except DataError as exc:
                raise UsageError('Invalid PostgreSQL time interval format') from exc
        conn.commit()
