# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom mocks for testing.
"""
import itertools

import psycopg2.extras

from nominatim.db import properties

# This must always point to the mock word table for the default tokenizer.
from mock_icu_word_table import MockIcuWordTable as MockWordTable

class MockPlacexTable:
    """ A placex table for testing.
    """
    def __init__(self, conn):
        self.idseq = itertools.count(10000)
        self.conn = conn
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE placex (
                               place_id BIGINT,
                               parent_place_id BIGINT,
                               linked_place_id BIGINT,
                               importance FLOAT,
                               indexed_date TIMESTAMP,
                               geometry_sector INTEGER,
                               rank_address SMALLINT,
                               rank_search SMALLINT,
                               partition SMALLINT,
                               indexed_status SMALLINT,
                               osm_id int8,
                               osm_type char(1),
                               class text,
                               type text,
                               name hstore,
                               admin_level smallint,
                               address hstore,
                               extratags hstore,
                               geometry Geometry(Geometry,4326),
                               wikipedia TEXT,
                               country_code varchar(2),
                               housenumber TEXT,
                               postcode TEXT,
                               centroid GEOMETRY(Geometry, 4326))""")
            cur.execute("CREATE SEQUENCE IF NOT EXISTS seq_place")
        conn.commit()

    def add(self, osm_type='N', osm_id=None, cls='amenity', typ='cafe', names=None,
            admin_level=None, address=None, extratags=None, geom='POINT(10 4)',
            country=None, housenumber=None):
        with self.conn.cursor() as cur:
            psycopg2.extras.register_hstore(cur)
            cur.execute("""INSERT INTO placex (place_id, osm_type, osm_id, class,
                                               type, name, admin_level, address,
                                               housenumber,
                                               extratags, geometry, country_code)
                            VALUES(nextval('seq_place'), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                        (osm_type, osm_id or next(self.idseq), cls, typ, names,
                         admin_level, address, housenumber, extratags, 'SRID=4326;' + geom,
                         country))
        self.conn.commit()


class MockPropertyTable:
    """ A property table for testing.
    """
    def __init__(self, conn):
        self.conn = conn


    def set(self, name, value):
        """ Set a property in the table to the given value.
        """
        properties.set_property(self.conn, name, value)


    def get(self, name):
        """ Set a property in the table to the given value.
        """
        return properties.get_property(self.conn, name)
