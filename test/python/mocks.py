# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Custom mocks for testing.
"""
import itertools

from nominatim_db.db import properties


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
                               token_info jsonb,
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
            country=None, housenumber=None, rank_search=30):
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO placex (place_id, osm_type, osm_id, class,
                                               type, name, admin_level, address,
                                               housenumber, rank_search,
                                               extratags, geometry, country_code)
                            VALUES(nextval('seq_place'), %s, %s, %s, %s, %s, %s,
                                   %s, %s, %s, %s, %s, %s)
                            RETURNING place_id""",
                        (osm_type, osm_id or next(self.idseq), cls, typ, names,
                         admin_level, address, housenumber, rank_search,
                         extratags, 'SRID=4326;' + geom,
                         country))
            place_id = cur.fetchone()[0]
        self.conn.commit()
        return place_id


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
