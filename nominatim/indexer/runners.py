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
from typing import Any, List
import functools

from psycopg2 import sql as pysql
import psycopg2.extras

from nominatim.data.place_info import PlaceInfo
from nominatim.tokenizer.base import AbstractAnalyzer
from nominatim.db.async_connection import DBConnection
from nominatim.typing import Query, DictCursorResult, DictCursorResults, Protocol

# pylint: disable=C0111

def _mk_valuelist(template: str, num: int) -> pysql.Composed:
    return pysql.SQL(',').join([pysql.SQL(template)] * num)

def _analyze_place(place: DictCursorResult, analyzer: AbstractAnalyzer) -> psycopg2.extras.Json:
    return psycopg2.extras.Json(analyzer.process_place(PlaceInfo(place)))


class Runner(Protocol):
    def name(self) -> str: ...
    def sql_count_objects(self) -> Query: ...
    def sql_get_objects(self) -> Query: ...
    def get_place_details(self, worker: DBConnection,
                          ids: DictCursorResults) -> DictCursorResults: ...
    def index_places(self, worker: DBConnection, places: DictCursorResults) -> None: ...


class AbstractPlacexRunner:
    """ Returns SQL commands for indexing of the placex table.
    """
    SELECT_SQL = pysql.SQL('SELECT place_id FROM placex ')
    UPDATE_LINE = "(%s, %s::hstore, %s::hstore, %s::int, %s::jsonb)"

    def __init__(self, rank: int, analyzer: AbstractAnalyzer) -> None:
        self.rank = rank
        self.analyzer = analyzer


    @functools.lru_cache(maxsize=1)
    def _index_sql(self, num_places: int) -> pysql.Composed:
        return pysql.SQL(
            """ UPDATE placex
                SET indexed_status = 0, address = v.addr, token_info = v.ti,
                    name = v.name, linked_place_id = v.linked_place_id
                FROM (VALUES {}) as v(id, name, addr, linked_place_id, ti)
                WHERE place_id = v.id
            """).format(_mk_valuelist(AbstractPlacexRunner.UPDATE_LINE, num_places))


    def get_place_details(self, worker: DBConnection, ids: DictCursorResults) -> DictCursorResults:
        worker.perform("""SELECT place_id, extra.*
                          FROM placex, LATERAL placex_indexing_prepare(placex) as extra
                          WHERE place_id IN %s""",
                       (tuple((p[0] for p in ids)), ))

        return []


    def index_places(self, worker: DBConnection, places: DictCursorResults) -> None:
        values: List[Any] = []
        for place in places:
            for field in ('place_id', 'name', 'address', 'linked_place_id'):
                values.append(place[field])
            values.append(_analyze_place(place, self.analyzer))

        worker.perform(self._index_sql(len(places)), values)


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
        return self.SELECT_SQL + pysql.SQL(
            """WHERE indexed_status > 0 and rank_address = {}
               ORDER BY geometry_sector
            """).format(pysql.Literal(self.rank))


class BoundaryRunner(AbstractPlacexRunner):
    """ Returns SQL commands for indexing the administrative boundaries
        of a certain rank.
    """

    def name(self) -> str:
        return f"boundaries rank {self.rank}"

    def sql_count_objects(self) -> pysql.Composed:
        return pysql.SQL("""SELECT count(*) FROM placex
                            WHERE indexed_status > 0
                              AND rank_search = {}
                              AND class = 'boundary' and type = 'administrative'
                         """).format(pysql.Literal(self.rank))

    def sql_get_objects(self) -> pysql.Composed:
        return self.SELECT_SQL + pysql.SQL(
            """WHERE indexed_status > 0 and rank_search = {}
                     and class = 'boundary' and type = 'administrative'
               ORDER BY partition, admin_level
            """).format(pysql.Literal(self.rank))


class InterpolationRunner:
    """ Returns SQL commands for indexing the address interpolation table
        location_property_osmline.
    """

    def __init__(self, analyzer: AbstractAnalyzer) -> None:
        self.analyzer = analyzer


    def name(self) -> str:
        return "interpolation lines (location_property_osmline)"

    def sql_count_objects(self) -> str:
        return """SELECT count(*) FROM location_property_osmline
                  WHERE indexed_status > 0"""

    def sql_get_objects(self) -> str:
        return """SELECT place_id
                  FROM location_property_osmline
                  WHERE indexed_status > 0
                  ORDER BY geometry_sector"""


    def get_place_details(self, worker: DBConnection, ids: DictCursorResults) -> DictCursorResults:
        worker.perform("""SELECT place_id, get_interpolation_address(address, osm_id) as address
                          FROM location_property_osmline WHERE place_id IN %s""",
                       (tuple((p[0] for p in ids)), ))
        return []


    @functools.lru_cache(maxsize=1)
    def _index_sql(self, num_places: int) -> pysql.Composed:
        return pysql.SQL("""UPDATE location_property_osmline
                            SET indexed_status = 0, address = v.addr, token_info = v.ti
                            FROM (VALUES {}) as v(id, addr, ti)
                            WHERE place_id = v.id
                         """).format(_mk_valuelist("(%s, %s::hstore, %s::jsonb)", num_places))


    def index_places(self, worker: DBConnection, places: DictCursorResults) -> None:
        values: List[Any] = []
        for place in places:
            values.extend((place[x] for x in ('place_id', 'address')))
            values.append(_analyze_place(place, self.analyzer))

        worker.perform(self._index_sql(len(places)), values)



class PostcodeRunner(Runner):
    """ Provides the SQL commands for indexing the location_postcode table.
    """

    def name(self) -> str:
        return "postcodes (location_postcode)"


    def sql_count_objects(self) -> str:
        return 'SELECT count(*) FROM location_postcode WHERE indexed_status > 0'


    def sql_get_objects(self) -> str:
        return """SELECT place_id FROM location_postcode
                  WHERE indexed_status > 0
                  ORDER BY country_code, postcode"""


    def get_place_details(self, worker: DBConnection, ids: DictCursorResults) -> DictCursorResults:
        return ids

    def index_places(self, worker: DBConnection, places: DictCursorResults) -> None:
        worker.perform(pysql.SQL("""UPDATE location_postcode SET indexed_status = 0
                                    WHERE place_id IN ({})""")
                       .format(pysql.SQL(',').join((pysql.Literal(i[0]) for i in places))))
