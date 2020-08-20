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

from argparse import ArgumentParser, RawDescriptionHelpFormatter, ArgumentTypeError
import logging
import sys
import re
import getpass
from datetime import datetime
import select

from indexer.progress import ProgressLogger
from indexer.db import DBConnection, make_connection

log = logging.getLogger()

class RankRunner(object):
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

    def sql_index_place(self, ids):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id IN ({})"\
               .format(','.join((str(i) for i in ids)))


class InterpolationRunner(object):
    """ Returns SQL commands for indexing the address interpolation table
        location_property_osmline.
    """

    def name(self):
        return "interpolation lines (location_property_osmline)"

    def sql_count_objects(self):
        return """SELECT count(*) FROM location_property_osmline
                  WHERE indexed_status > 0"""

    def sql_get_objects(self):
        return """SELECT place_id FROM location_property_osmline
                  WHERE indexed_status > 0
                  ORDER BY geometry_sector"""

    def sql_index_place(self, ids):
        return """UPDATE location_property_osmline
                  SET indexed_status = 0 WHERE place_id IN ({})"""\
               .format(','.join((str(i) for i in ids)))

class BoundaryRunner(object):
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

    def sql_index_place(self, ids):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id IN ({})"\
               .format(','.join((str(i) for i in ids)))

class Indexer(object):
    """ Main indexing routine.
    """

    def __init__(self, options):
        self.minrank = max(1, options.minrank)
        self.maxrank = min(30, options.maxrank)
        self.conn = make_connection(options)
        self.threads = [DBConnection(options) for i in range(options.threads)]

    def index_boundaries(self):
        log.warning("Starting indexing boundaries using {} threads".format(
                      len(self.threads)))

        for rank in range(max(self.minrank, 5), min(self.maxrank, 26)):
            self.index(BoundaryRunner(rank))

    def index_by_rank(self):
        """ Run classic indexing by rank.
        """
        log.warning("Starting indexing rank ({} to {}) using {} threads".format(
                 self.minrank, self.maxrank, len(self.threads)))

        for rank in range(max(1, self.minrank), self.maxrank):
            self.index(RankRunner(rank))


        if self.maxrank == 30:
            self.index(RankRunner(0), 20)
            self.index(InterpolationRunner(), 20)

        self.index(RankRunner(self.maxrank), 20)

    def index(self, obj, batch=1):
        """ Index a single rank or table. `obj` describes the SQL to use
            for indexing. `batch` describes the number of objects that
            should be processed with a single SQL statement
        """
        log.warning("Starting {}".format(obj.name()))

        cur = self.conn.cursor()
        cur.execute(obj.sql_count_objects())

        total_tuples = cur.fetchone()[0]
        log.debug("Total number of rows: {}".format(total_tuples))

        cur.close()

        progress = ProgressLogger(obj.name(), total_tuples)

        if total_tuples > 0:
            cur = self.conn.cursor(name='places')
            cur.execute(obj.sql_get_objects())

            next_thread = self.find_free_thread()
            while True:
                places = [p[0] for p in cur.fetchmany(batch)]
                if len(places) == 0:
                    break

                log.debug("Processing places: {}".format(places))
                thread = next(next_thread)

                thread.perform(obj.sql_index_place(places))
                progress.add(len(places))

            cur.close()

            for t in self.threads:
                t.wait()

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
                for t in self.threads:
                    while not t.is_done():
                        t.wait()
                    t.connect()
                command_stat = 0
                ready = self.threads
            else:
                ready, _, _ = select.select(self.threads, [], [])

        assert False, "Unreachable code"


def nominatim_arg_parser():
    """ Setup the command-line parser for the tool.
    """
    def h(s):
        return re.sub("\s\s+" , " ", s)

    p = ArgumentParser(description="Indexing tool for Nominatim.",
                       formatter_class=RawDescriptionHelpFormatter)

    p.add_argument('-d', '--database',
                   dest='dbname', action='store', default='nominatim',
                   help='Name of the PostgreSQL database to connect to.')
    p.add_argument('-U', '--username',
                   dest='user', action='store',
                   help='PostgreSQL user name.')
    p.add_argument('-W', '--password',
                   dest='password_prompt', action='store_true',
                   help='Force password prompt.')
    p.add_argument('-H', '--host',
                   dest='host', action='store',
                   help='PostgreSQL server hostname or socket location.')
    p.add_argument('-P', '--port',
                   dest='port', action='store',
                   help='PostgreSQL server port')
    p.add_argument('-b', '--boundary-only',
                   dest='boundary_only', action='store_true',
                   help='Only index administrative boundaries (ignores min/maxrank).')
    p.add_argument('-r', '--minrank',
                   dest='minrank', type=int, metavar='RANK', default=0,
                   help='Minimum/starting rank.')
    p.add_argument('-R', '--maxrank',
                   dest='maxrank', type=int, metavar='RANK', default=30,
                   help='Maximum/finishing rank.')
    p.add_argument('-t', '--threads',
                   dest='threads', type=int, metavar='NUM', default=1,
                   help='Number of threads to create for indexing.')
    p.add_argument('-v', '--verbose',
                   dest='loglevel', action='count', default=0,
                   help='Increase verbosity')

    return p

if __name__ == '__main__':
    logging.basicConfig(stream=sys.stderr, format='%(levelname)s: %(message)s')

    options = nominatim_arg_parser().parse_args(sys.argv[1:])

    log.setLevel(max(3 - options.loglevel, 0) * 10)

    options.password = None
    if options.password_prompt:
        password = getpass.getpass("Database password: ")
        options.password = password

    if options.boundary_only:
        Indexer(options).index_boundaries()
    else:
        Indexer(options).index_by_rank()
