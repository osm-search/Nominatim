#! /usr/bin/env python3
#-----------------------------------------------------------------------------
# nominatim - [description]
#-----------------------------------------------------------------------------
#
# Indexing tool for the Nominatim database.
#
# Based on C version by Brian Quinion
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#-----------------------------------------------------------------------------
# pylint: disable=C0111
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
import sys
import getpass
import select

from indexer.progress import ProgressLogger # pylint: disable=E0401
from indexer.db import DBConnection, make_connection # pylint: disable=E0401

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

    def __init__(self, opts):
        self.minrank = max(1, opts.minrank)
        self.maxrank = min(30, opts.maxrank)
        self.conn = make_connection(opts)
        self.threads = [DBConnection(opts) for _ in range(opts.threads)]

    def index_boundaries(self):
        LOG.warning("Starting indexing boundaries using %s threads",
                    len(self.threads))

        for rank in range(max(self.minrank, 5), min(self.maxrank, 26)):
            self.index(BoundaryRunner(rank))

    def index_by_rank(self):
        """ Run classic indexing by rank.
        """
        LOG.warning("Starting indexing rank (%i to %i) using %i threads",
                    self.minrank, self.maxrank, len(self.threads))

        for rank in range(max(1, self.minrank), self.maxrank):
            self.index(RankRunner(rank))

        if self.maxrank == 30:
            self.index(RankRunner(0))
            self.index(InterpolationRunner(), 20)
            self.index(RankRunner(self.maxrank), 20)
        else:
            self.index(RankRunner(self.maxrank))

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


def nominatim_arg_parser():
    """ Setup the command-line parser for the tool.
    """
    parser = ArgumentParser(description="Indexing tool for Nominatim.",
                            formatter_class=RawDescriptionHelpFormatter)

    parser.add_argument('-d', '--database',
                        dest='dbname', action='store', default='nominatim',
                        help='Name of the PostgreSQL database to connect to.')
    parser.add_argument('-U', '--username',
                        dest='user', action='store',
                        help='PostgreSQL user name.')
    parser.add_argument('-W', '--password',
                        dest='password_prompt', action='store_true',
                        help='Force password prompt.')
    parser.add_argument('-H', '--host',
                        dest='host', action='store',
                        help='PostgreSQL server hostname or socket location.')
    parser.add_argument('-P', '--port',
                        dest='port', action='store',
                        help='PostgreSQL server port')
    parser.add_argument('-b', '--boundary-only',
                        dest='boundary_only', action='store_true',
                        help='Only index administrative boundaries (ignores min/maxrank).')
    parser.add_argument('-r', '--minrank',
                        dest='minrank', type=int, metavar='RANK', default=0,
                        help='Minimum/starting rank.')
    parser.add_argument('-R', '--maxrank',
                        dest='maxrank', type=int, metavar='RANK', default=30,
                        help='Maximum/finishing rank.')
    parser.add_argument('-t', '--threads',
                        dest='threads', type=int, metavar='NUM', default=1,
                        help='Number of threads to create for indexing.')
    parser.add_argument('-v', '--verbose',
                        dest='loglevel', action='count', default=0,
                        help='Increase verbosity')

    return parser

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, format='%(levelname)s: %(message)s')

    OPTIONS = nominatim_arg_parser().parse_args(sys.argv[1:])

    LOG.setLevel(max(3 - OPTIONS.loglevel, 0) * 10)

    OPTIONS.password = None
    if OPTIONS.password_prompt:
        PASSWORD = getpass.getpass("Database password: ")
        OPTIONS.password = PASSWORD

    if OPTIONS.boundary_only:
        Indexer(OPTIONS).index_boundaries()
    else:
        Indexer(OPTIONS).index_by_rank()
