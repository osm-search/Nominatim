# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for database analysis and maintenance.
"""
import logging

from nominatim.errors import UsageError

LOG = logging.getLogger()

def analyse_indexing(conn, osm_id=None, place_id=None):
    """ Analyse indexing of a single Nominatim object.
    """
    with conn.cursor() as cur:
        if osm_id:
            osm_type = osm_id[0].upper()
            if osm_type not in 'NWR' or not osm_id[1:].isdigit():
                LOG.fatal('OSM ID must be of form <N|W|R><id>. Got: %s', osm_id)
                raise UsageError("OSM ID parameter badly formatted")
            cur.execute('SELECT place_id FROM placex WHERE osm_type = %s AND osm_id = %s',
                        (osm_type, osm_id[1:]))

            if cur.rowcount < 1:
                LOG.fatal("OSM object %s not found in database.", osm_id)
                raise UsageError("OSM object not found")

            place_id = cur.fetchone()[0]

        if place_id is None:
            LOG.fatal("No OSM object given to index.")
            raise UsageError("OSM object not found")

        cur.execute("update placex set indexed_status = 2 where place_id = %s",
                    (place_id, ))

        cur.execute("""SET auto_explain.log_min_duration = '0';
                       SET auto_explain.log_analyze = 'true';
                       SET auto_explain.log_nested_statements = 'true';
                       LOAD 'auto_explain';
                       SET client_min_messages = LOG;
                       SET log_min_messages = FATAL""")

        cur.execute("update placex set indexed_status = 0 where place_id = %s",
                    (place_id, ))

    # we do not want to keep the results
    conn.rollback()

    for msg in conn.notices:
        print(msg)
