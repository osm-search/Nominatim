"""
Functions to facilitate accessing and comparing the content of DB tables.
"""
import re

ID_REGEX = re.compile(r"(?P<typ>[NRW])(?P<oid>\d+)(:(?P<cls>\w+))?")

class NominatimID:
    """ Splits a unique identifier for places into its components.
        As place_ids cannot be used for testing, we use a unique
        identifier instead that is of the form <osmtype><osmid>[:<class>].
    """

    def __init__(self, oid):
        self.typ = self.oid = self.cls = None

        if oid is not None:
            m = ID_REGEX.fullmatch(oid)
            assert m is not None, \
                   "ID '{}' not of form <osmtype><osmid>[:<class>]".format(oid)

            self.typ = m.group('typ')
            self.oid = m.group('oid')
            self.cls = m.group('cls')

    def __str__(self):
        if self.cls is None:
            return self.typ + self.oid

        return '{self.typ}{self.oid}:{self.cls}'.format(self=self)

    def query_osm_id(self, cur, query):
        """ Run a query on cursor `cur` using osm ID, type and class. The
            `query` string must contain exactly one placeholder '{}' where
            the 'where' query should go.
        """
        where = 'osm_type = %s and osm_id = %s'
        params = [self.typ, self. oid]

        if self.cls is not None:
            where += ' and class = %s'
            params.append(self.cls)

        return cur.execute(query.format(where), params)

    def query_place_id(self, cur, query):
        """ Run a query on cursor `cur` using the place ID. The `query` string
            must contain exactly one placeholder '%s' where the 'where' query
            should go.
        """
        pid = self.get_place_id(cur)
        return cur.execute(query, (pid, ))

    def get_place_id(self, cur):
        """ Look up the place id for the ID. Throws an assertion if the ID
            is not unique.
        """
        self.query_osm_id(cur, "SELECT place_id FROM placex WHERE {}")
        assert cur.rowcount == 1, \
               "Place ID {!s} not unique. Found {} entries.".format(self, cur.rowcount)

        return cur.fetchone()[0]
