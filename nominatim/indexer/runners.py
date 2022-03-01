# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Mix-ins that provide the actual commands for the indexer for various indexing
tasks.
"""
import functools

from psycopg2 import sql as pysql

from nominatim.indexer.place_info import PlaceInfo

# pylint: disable=C0111

def _mk_valuelist(template, num):
    return pysql.SQL(',').join([pysql.SQL(template)] * num)


class AbstractPlacexRunner:
    """ Returns SQL commands for indexing of the placex table.
    """
    SELECT_SQL = pysql.SQL('SELECT place_id FROM placex ')
    UPDATE_LINE = "(%s, %s::hstore, %s::hstore, %s::int, %s::jsonb)"

    def __init__(self, rank, analyzer):
        self.rank = rank
        self.analyzer = analyzer


    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _index_sql(num_places):
        return pysql.SQL(
            """ UPDATE placex
                SET indexed_status = 0, address = v.addr, token_info = v.ti,
                    name = v.name, linked_place_id = v.linked_place_id
                FROM (VALUES {}) as v(id, name, addr, linked_place_id, ti)
                WHERE place_id = v.id
            """).format(_mk_valuelist(AbstractPlacexRunner.UPDATE_LINE, num_places))


    @staticmethod
    def get_place_details(worker, ids):
        worker.perform("""SELECT place_id, extra.*
                          FROM placex, LATERAL placex_indexing_prepare(placex) as extra
                          WHERE place_id IN %s""",
                       (tuple((p[0] for p in ids)), ))


    def index_places(self, worker, places):
        values = []
        for place in places:
            for field in ('place_id', 'name', 'address', 'linked_place_id'):
                values.append(place[field])
            values.append(PlaceInfo(place).analyze(self.analyzer))

        worker.perform(self._index_sql(len(places)), values)


class RankRunner(AbstractPlacexRunner):
    """ Returns SQL commands for indexing one rank within the placex table.
    """

    def name(self):
        return "rank {}".format(self.rank)

    def sql_count_objects(self):
        return pysql.SQL("""SELECT count(*) FROM placex
                            WHERE rank_address = {} and indexed_status > 0
                         """).format(pysql.Literal(self.rank))

    def sql_get_objects(self):
        return self.SELECT_SQL + pysql.SQL(
            """WHERE indexed_status > 0 and rank_address = {}
               ORDER BY geometry_sector
            """).format(pysql.Literal(self.rank))


class BoundaryRunner(AbstractPlacexRunner):
    """ Returns SQL commands for indexing the administrative boundaries
        of a certain rank.
    """

    def name(self):
        return "boundaries rank {}".format(self.rank)

    def sql_count_objects(self):
        return pysql.SQL("""SELECT count(*) FROM placex
                            WHERE indexed_status > 0
                              AND rank_search = {}
                              AND class = 'boundary' and type = 'administrative'
                         """).format(pysql.Literal(self.rank))

    def sql_get_objects(self):
        return self.SELECT_SQL + pysql.SQL(
            """WHERE indexed_status > 0 and rank_search = {}
                     and class = 'boundary' and type = 'administrative'
               ORDER BY partition, admin_level
            """).format(pysql.Literal(self.rank))


class InterpolationRunner:
    """ Returns SQL commands for indexing the address interpolation table
        location_property_osmline.
    """

    def __init__(self, analyzer):
        self.analyzer = analyzer


    @staticmethod
    def name():
        return "interpolation lines (location_property_osmline)"

    @staticmethod
    def sql_count_objects():
        return """SELECT count(*) FROM location_property_osmline
                  WHERE indexed_status > 0"""

    @staticmethod
    def sql_get_objects():
        return """SELECT place_id
                  FROM location_property_osmline
                  WHERE indexed_status > 0
                  ORDER BY geometry_sector"""


    @staticmethod
    def get_place_details(worker, ids):
        worker.perform("""SELECT place_id, get_interpolation_address(address, osm_id) as address
                          FROM location_property_osmline WHERE place_id IN %s""",
                       (tuple((p[0] for p in ids)), ))


    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _index_sql(num_places):
        return pysql.SQL("""UPDATE location_property_osmline
                            SET indexed_status = 0, address = v.addr, token_info = v.ti
                            FROM (VALUES {}) as v(id, addr, ti)
                            WHERE place_id = v.id
                         """).format(_mk_valuelist("(%s, %s::hstore, %s::jsonb)", num_places))


    def index_places(self, worker, places):
        values = []
        for place in places:
            values.extend((place[x] for x in ('place_id', 'address')))
            values.append(PlaceInfo(place).analyze(self.analyzer))

        worker.perform(self._index_sql(len(places)), values)



class PostcodeRunner:
    """ Provides the SQL commands for indexing the location_postcode table.
    """

    @staticmethod
    def name():
        return "postcodes (location_postcode)"

    @staticmethod
    def sql_count_objects():
        return 'SELECT count(*) FROM location_postcode WHERE indexed_status > 0'

    @staticmethod
    def sql_get_objects():
        return """SELECT place_id FROM location_postcode
                  WHERE indexed_status > 0
                  ORDER BY country_code, postcode"""

    @staticmethod
    def index_places(worker, ids):
        worker.perform(pysql.SQL("""UPDATE location_postcode SET indexed_status = 0
                                    WHERE place_id IN ({})""")
                       .format(pysql.SQL(',').join((pysql.Literal(i[0]) for i in ids))))
