"""
Mix-ins that provide the actual commands for the indexer for various indexing
tasks.
"""
# pylint: disable=C0111

class RankRunner:
    """ Returns SQL commands for indexing one rank within the placex table.
    """

    def __init__(self, rank):
        self.rank = rank

    def name(self):
        return "rank {}".format(self.rank)

    def sql_count_objects(self):
        return """SELECT count(*) FROM placex
                  WHERE rank_address = {} and indexed_status > 0
               """.format(self.rank)

    def sql_get_objects(self):
        return """SELECT place_id FROM placex
                  WHERE indexed_status > 0 and rank_address = {}
                  ORDER BY geometry_sector""".format(self.rank)

    @staticmethod
    def sql_index_place(ids):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id IN ({})"\
               .format(','.join((str(i) for i in ids)))


class BoundaryRunner:
    """ Returns SQL commands for indexing the administrative boundaries
        of a certain rank.
    """

    def __init__(self, rank):
        self.rank = rank

    def name(self):
        return "boundaries rank {}".format(self.rank)

    def sql_count_objects(self):
        return """SELECT count(*) FROM placex
                  WHERE indexed_status > 0
                    AND rank_search = {}
                    AND class = 'boundary' and type = 'administrative'
               """.format(self.rank)

    def sql_get_objects(self):
        return """SELECT place_id FROM placex
                  WHERE indexed_status > 0 and rank_search = {}
                        and class = 'boundary' and type = 'administrative'
                  ORDER BY partition, admin_level
               """.format(self.rank)

    @staticmethod
    def sql_index_place(ids):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id IN ({})"\
               .format(','.join((str(i) for i in ids)))


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
    def sql_index_place(ids):
        return """UPDATE location_property_osmline
                  SET indexed_status = 0 WHERE place_id IN ({})
               """.format(','.join((str(i) for i in ids)))


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
    def sql_index_place(ids):
        return """UPDATE location_postcode SET indexed_status = 0
                  WHERE place_id IN ({})
               """.format(','.join((str(i) for i in ids)))
