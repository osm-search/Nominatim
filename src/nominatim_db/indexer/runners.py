# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Mix-ins that provide the actual commands for the indexer for various indexing
tasks.
"""
from psycopg import sql as pysql

from ..typing import Protocol, QueryNoTemplate


def _mk_valuelist(template: str, num: int) -> pysql.Composed:
    return pysql.SQL(',').join([pysql.SQL(template)] * num)


class Runner(Protocol):
    QUERY_ROWS: list[str] = []
    def name(self) -> str: ...
    def sql_count_objects(self) -> QueryNoTemplate: ...
    def sql_get_objects(self) -> QueryNoTemplate: ...
    def index_places_query(self, batch_size: int) -> QueryNoTemplate: ...


SELECT_SQL = pysql.SQL("""SELECT place_id, extra.*
                          FROM (SELECT * FROM placex {}) as px,
                          LATERAL placex_indexing_prepare(px) as extra """)
UPDATE_LINE = "(%s, %s::hstore, %s::hstore, %s::int, %s::jsonb)"


class AbstractPlacexRunner:
    """ Returns SQL commands for indexing of the placex table.
    """
    QUERY_ROWS = ['place_id', 'name', 'address', 'linked_place_id', 'token_info']

    def __init__(self, rank: int) -> None:
        self.rank = rank

    def index_places_query(self, batch_size: int) -> QueryNoTemplate:
        return pysql.SQL(
            """ UPDATE placex
                SET indexed_status = 0, address = v.addr, token_info = v.ti,
                    name = v.name, linked_place_id = v.linked_place_id
                FROM (VALUES {}) as v(id, name, addr, linked_place_id, ti)
                WHERE place_id = v.id
            """).format(_mk_valuelist(UPDATE_LINE, batch_size))


class RankRunner(AbstractPlacexRunner):
    """ Returns SQL commands for indexing one rank within the placex table.
    """

    def name(self) -> str:
        return f"rank {self.rank}"

    def sql_count_objects(self) -> pysql.Composed:
        return pysql.SQL("""SELECT count(*) FROM placex
                            WHERE rank_address = {} and indexed_status > 0
                         """).format(pysql.Literal(self.rank))

    def sql_get_objects(self) -> pysql.Composed:
        return SELECT_SQL.format(pysql.SQL(
                """WHERE placex.indexed_status > 0 and placex.rank_address = {}
                   ORDER BY placex.geometry_sector
                """).format(pysql.Literal(self.rank)))


class BoundaryRunner(AbstractPlacexRunner):
    """ Returns SQL commands for indexing the administrative boundaries
        of a certain rank.
    """

    def name(self) -> str:
        return f"boundaries rank {self.rank}"

    def sql_count_objects(self) -> QueryNoTemplate:
        return pysql.SQL("""SELECT count(*) FROM placex
                            WHERE indexed_status > 0
                              AND rank_search = {}
                              AND categories <@ 'osm.boundary.administrative'
                        """).format(pysql.Literal(self.rank))

    def sql_get_objects(self) -> QueryNoTemplate:
        return SELECT_SQL.format(pysql.SQL(
                """WHERE placex.indexed_status > 0 and placex.rank_search = {}
                         and placex.categories <@ 'osm.boundary.administrative'
                   ORDER BY placex.partition, placex.admin_level
                """).format(pysql.Literal(self.rank)))


class InterpolationRunner:
    """ Returns SQL commands for indexing the address interpolation table
        location_property_osmline.
    """
    QUERY_ROWS = ['place_id', 'address', 'token_info']

    def name(self) -> str:
        return "interpolation lines (location_property_osmline)"

    def sql_count_objects(self) -> QueryNoTemplate:
        return """SELECT count(*) FROM location_property_osmline
                  WHERE indexed_status > 0"""

    def sql_get_objects(self) -> QueryNoTemplate:
        return """SELECT place_id, get_interpolation_address(address, osm_id) as address
                  FROM location_property_osmline
                  WHERE indexed_status > 0
                  ORDER BY geometry_sector"""

    def index_places_query(self, batch_size: int) -> QueryNoTemplate:
        return pysql.SQL("""UPDATE location_property_osmline
                            SET indexed_status = 0, address = v.addr, token_info = v.ti
                            FROM (VALUES {}) as v(id, addr, ti)
                            WHERE place_id = v.id
                         """).format(_mk_valuelist("(%s, %s::hstore, %s::jsonb)", batch_size))


class PostcodeRunner(Runner):
    """ Provides the SQL commands for indexing the location_postcodes table.
    """
    QUERY_ROWS = ['place_id']

    def name(self) -> str:
        return "postcodes (location_postcodes)"

    def sql_count_objects(self) -> QueryNoTemplate:
        return 'SELECT count(*) FROM location_postcodes WHERE indexed_status > 0'

    def sql_get_objects(self) -> QueryNoTemplate:
        return """SELECT place_id FROM location_postcodes
                  WHERE indexed_status > 0
                  ORDER BY country_code, postcode"""

    def index_places_query(self, batch_size: int) -> QueryNoTemplate:
        return pysql.SQL("""UPDATE location_postcodes SET indexed_status = 0
                                    WHERE place_id IN ({})""")\
                    .format(pysql.SQL(',').join((pysql.Placeholder() for _ in range(batch_size))))
