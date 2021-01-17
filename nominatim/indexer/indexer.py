"""
Main work horse for indexing (computing addresses) the database.
"""
# pylint: disable=C0111
import logging
import select

import psycopg2

from .progress import ProgressLogger
from ..db.async_connection import DBConnection

LOG = logging.getLogger()

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
                  SET indexed_status = 0 WHERE place_id IN ({})"""\
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
                    AND class = 'boundary' and type = 'administrative'""".format(self.rank)

    def sql_get_objects(self):
        return """SELECT place_id FROM placex
                  WHERE indexed_status > 0 and rank_search = {}
                        and class = 'boundary' and type = 'administrative'
                  ORDER BY partition, admin_level""".format(self.rank)

    @staticmethod
    def sql_index_place(ids):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id IN ({})"\
               .format(','.join((str(i) for i in ids)))

class Indexer:
    """ Main indexing routine.
    """

    def __init__(self, dsn, num_threads):
        self.conn = psycopg2.connect(dsn)
        self.threads = [DBConnection(dsn) for _ in range(num_threads)]

    def index_boundaries(self, minrank, maxrank):
        LOG.warning("Starting indexing boundaries using %s threads",
                    len(self.threads))

        for rank in range(max(minrank, 5), min(maxrank, 26)):
            self.index(BoundaryRunner(rank))

    def index_by_rank(self, minrank, maxrank):
        """ Run classic indexing by rank.
        """
        maxrank = min(maxrank, 30)
        LOG.warning("Starting indexing rank (%i to %i) using %i threads",
                    minrank, maxrank, len(self.threads))

        for rank in range(max(1, minrank), maxrank):
            self.index(RankRunner(rank))

        if maxrank == 30:
            self.index(RankRunner(0))
            self.index(InterpolationRunner(), 20)
            self.index(RankRunner(30), 20)
        else:
            self.index(RankRunner(maxrank))

    def index(self, obj, batch=1):
        """ Index a single rank or table. `obj` describes the SQL to use
            for indexing. `batch` describes the number of objects that
            should be processed with a single SQL statement
        """
        LOG.warning("Starting %s (using batch size %s)", obj.name(), batch)

        cur = self.conn.cursor()
        cur.execute(obj.sql_count_objects())

        total_tuples = cur.fetchone()[0]
        LOG.debug("Total number of rows: %i", total_tuples)

        cur.close()

        progress = ProgressLogger(obj.name(), total_tuples)

        if total_tuples > 0:
            cur = self.conn.cursor(name='places')
            cur.execute(obj.sql_get_objects())

            next_thread = self.find_free_thread()
            while True:
                places = [p[0] for p in cur.fetchmany(batch)]
                if not places:
                    break

                LOG.debug("Processing places: %s", str(places))
                thread = next(next_thread)

                thread.perform(obj.sql_index_place(places))
                progress.add(len(places))

            cur.close()

            for thread in self.threads:
                thread.wait()

        progress.done()

    def find_free_thread(self):
        """ Generator that returns the next connection that is free for
            sending a query.
        """
        ready = self.threads
        command_stat = 0

        while True:
            for thread in ready:
                if thread.is_done():
                    command_stat += 1
                    yield thread

            # refresh the connections occasionaly to avoid potential
            # memory leaks in Postgresql.
            if command_stat > 100000:
                for thread in self.threads:
                    while not thread.is_done():
                        thread.wait()
                    thread.connect()
                command_stat = 0
                ready = self.threads
            else:
                ready, _, _ = select.select(self.threads, [], [])

        assert False, "Unreachable code"
