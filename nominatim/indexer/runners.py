"""
Mix-ins that provide the actual commands for the indexer for various indexing
tasks.
"""
import functools

import psycopg2.extras

# pylint: disable=C0111

class AbstractPlacexRunner:
    """ Returns SQL commands for indexing of the placex table.
    """
    SELECT_SQL = 'SELECT place_id, (placex_prepare_update(placex)).* FROM placex'

    def __init__(self, rank, analyzer):
        self.rank = rank
        self.analyzer = analyzer


    @staticmethod
    @functools.lru_cache(maxsize=1)
    def _index_sql(num_places):
        return """ UPDATE placex
                   SET indexed_status = 0, address = v.addr, token_info = v.ti
                   FROM (VALUES {}) as v(id, addr, ti)
                   WHERE place_id = v.id
               """.format(','.join(["(%s, %s::hstore, %s::json)"]  * num_places))


    def index_places(self, worker, places):
        values = []
        for place in places:
            values.extend((place[x] for x in ('place_id', 'address')))
            values.append(psycopg2.extras.Json(self.analyzer.process_place(place)))

        worker.perform(self._index_sql(len(places)), values)


class RankRunner(AbstractPlacexRunner):
    """ Returns SQL commands for indexing one rank within the placex table.
    """

    def name(self):
        return "rank {}".format(self.rank)

    def sql_count_objects(self):
        return """SELECT count(*) FROM placex
                  WHERE rank_address = {} and indexed_status > 0
               """.format(self.rank)

    def sql_get_objects(self):
        return """{} WHERE indexed_status > 0 and rank_address = {}
                     ORDER BY geometry_sector
               """.format(self.SELECT_SQL, self.rank)


class BoundaryRunner(AbstractPlacexRunner):
    """ Returns SQL commands for indexing the administrative boundaries
        of a certain rank.
    """

    def name(self):
        return "boundaries rank {}".format(self.rank)

    def sql_count_objects(self):
        return """SELECT count(*) FROM placex
                  WHERE indexed_status > 0
                    AND rank_search = {}
                    AND class = 'boundary' and type = 'administrative'
               """.format(self.rank)

    def sql_get_objects(self):
        return """{} WHERE indexed_status > 0 and rank_search = {}
                           and class = 'boundary' and type = 'administrative'
                     ORDER BY partition, admin_level
               """.format(self.SELECT_SQL, self.rank)


class InterpolationRunner:
    """ Returns SQL commands for indexing the address interpolation table
        location_property_osmline.
    """

    @staticmethod
    def name():
        return "interpolation lines (location_property_osmline)"

    @staticmethod
    def sql_count_objects():
        return """SELECT count(*) FROM location_property_osmline
                  WHERE indexed_status > 0"""

    @staticmethod
    def sql_get_objects():
        return """SELECT place_id FROM location_property_osmline
                  WHERE indexed_status > 0
                  ORDER BY geometry_sector"""

    @staticmethod
    def index_places(worker, ids):
        worker.perform(""" UPDATE location_property_osmline
                           SET indexed_status = 0 WHERE place_id IN ({})
                       """.format(','.join((str(i[0]) for i in ids))))


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
        worker.perform(""" UPDATE location_postcode SET indexed_status = 0
                           WHERE place_id IN ({})
                       """.format(','.join((str(i[0]) for i in ids))))
