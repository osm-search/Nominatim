#! /usr/bin/env python
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
import psycopg2
from psycopg2.extras import wait_select
import select

log = logging.getLogger()

def make_connection(options, asynchronous=False):
    return psycopg2.connect(dbname=options.dbname, user=options.user,
                            password=options.password, host=options.host,
                            port=options.port, async_=asynchronous)


class RankRunner(object):
    """ Returns SQL commands for indexing one rank within the placex table.
    """

    def __init__(self, rank):
        self.rank = rank

    def name(self):
        return "rank {}".format(self.rank)

    def sql_index_sectors(self):
        return """SELECT geometry_sector, count(*) FROM placex
                  WHERE rank_search = {} and indexed_status > 0
                  GROUP BY geometry_sector
                  ORDER BY geometry_sector""".format(self.rank)

    def sql_nosector_places(self):
        return """SELECT place_id FROM placex
                  WHERE indexed_status > 0 and rank_search = {}
                  ORDER BY geometry_sector""".format(self.rank)

    def sql_sector_places(self):
        return """SELECT place_id FROM placex
                  WHERE indexed_status > 0 and rank_search = {}
                        and geometry_sector = %s""".format(self.rank)

    def sql_index_place(self):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id = %s"


class InterpolationRunner(object):
    """ Returns SQL commands for indexing the address interpolation table
        location_property_osmline.
    """

    def name(self):
        return "interpolation lines (location_property_osmline)"

    def sql_index_sectors(self):
        return """SELECT geometry_sector, count(*) FROM location_property_osmline
                  WHERE indexed_status > 0
                  GROUP BY geometry_sector
                  ORDER BY geometry_sector"""

    def sql_nosector_places(self):
        return """SELECT place_id FROM location_property_osmline
                  WHERE indexed_status > 0
                  ORDER BY geometry_sector"""

    def sql_sector_places(self):
        return """SELECT place_id FROM location_property_osmline
                  WHERE indexed_status > 0 and geometry_sector = %s
                  ORDER BY geometry_sector"""

    def sql_index_place(self):
        return """UPDATE location_property_osmline
                  SET indexed_status = 0 WHERE place_id = %s"""


class DBConnection(object):
    """ A signle non-blocking database connection.
    """

    def __init__(self, options):
        self.conn = make_connection(options, asynchronous=True)
        self.wait()

        self.cursor = self.conn.cursor()

        self.current_query = None
        self.current_params = None

    def wait(self):
        """ Block until any pending operation is done.
        """
        wait_select(self.conn)
        self.current_query = None

    def perform(self, sql, args=None):
        """ Send SQL query to the server. Returns immediately without
            blocking.
        """
        self.current_query = sql
        self.current_params = args
        self.cursor.execute(sql, args)

    def fileno(self):
        """ File descriptor to wait for. (Makes this class select()able.)
        """
        return self.conn.fileno()

    def is_done(self):
        """ Check if the connection is available for a new query.

            Also checks if the previous query has run into a deadlock.
            If so, then the previous query is repeated.
        """
        if self.current_query is None:
            return True

        try:
            if self.conn.poll() == psycopg2.extensions.POLL_OK:
                self.current_query = None
                return True
        except psycopg2.extensions.TransactionRollbackError as e:
            if e.pgcode == '40P01':
                log.debug("Deadlock detected, retry.")
                self.cursor.execute(self.current_query, self.current_params)
            else:
                raise

        return False


class Indexer(object):
    """ Main indexing routine.
    """

    def __init__(self, options):
        self.minrank = max(0, options.minrank)
        self.maxrank = min(30, options.maxrank)
        self.conn = make_connection(options)
        self.threads = [DBConnection(options) for i in range(options.threads)]

    def run(self):
        """ Run indexing over the entire database.
        """
        log.warning("Starting indexing rank ({} to {}) using {} threads".format(
                 self.minrank, self.maxrank, len(self.threads)))

        for rank in range(self.minrank, self.maxrank):
            self.index(RankRunner(rank))

        if self.maxrank == 30:
            self.index(InterpolationRunner())
            self.index(RankRunner(30))

    def index(self, obj):
        """ Index a single rank or table. `obj` describes the SQL to use
            for indexing.
        """
        log.warning("Starting {}".format(obj.name()))

        cur = self.conn.cursor(name='main')
        cur.execute(obj.sql_index_sectors())

        total_tuples = 0
        for r in cur:
            total_tuples += r[1]
        log.debug("Total number of rows; {}".format(total_tuples))

        cur.scroll(0, mode='absolute')

        next_thread = self.find_free_thread()
        done_tuples = 0
        rank_start_time = datetime.now()

        sector_sql = obj.sql_sector_places()
        index_sql = obj.sql_index_place()
        min_grouped_tuples = total_tuples - len(self.threads) * 1000

        next_info = 100 if log.isEnabledFor(logging.INFO) else total_tuples + 1

        for r in cur:
            sector = r[0]

            # Should we do the remaining ones together?
            do_all = done_tuples > min_grouped_tuples

            pcur = self.conn.cursor(name='places')

            if do_all:
                pcur.execute(obj.sql_nosector_places())
            else:
                pcur.execute(sector_sql, (sector, ))

            for place in pcur:
                place_id = place[0]
                log.debug("Processing place {}".format(place_id))
                thread = next(next_thread)

                thread.perform(index_sql, (place_id,))
                done_tuples += 1

                if done_tuples >= next_info:
                    now = datetime.now()
                    done_time = (now - rank_start_time).total_seconds()
                    tuples_per_sec = done_tuples / done_time
                    log.info("Done {} in {} @ {:.3f} per second - {} ETA (seconds): {:.2f}"
                           .format(done_tuples, int(done_time),
                                   tuples_per_sec, obj.name(),
                                   (total_tuples - done_tuples)/tuples_per_sec))
                    next_info += int(tuples_per_sec)

            pcur.close()

            if do_all:
                break

        cur.close()

        for t in self.threads:
            t.wait()

        rank_end_time = datetime.now()
        diff_seconds = (rank_end_time-rank_start_time).total_seconds()

        log.warning("Done {}/{} in {} @ {:.3f} per second - FINISHED {}\n".format(
                 done_tuples, total_tuples, int(diff_seconds),
                 done_tuples/diff_seconds, obj.name()))

    def find_free_thread(self):
        """ Generator that returns the next connection that is free for
            sending a query.
        """
        ready = self.threads

        while True:
            for thread in ready:
                if thread.is_done():
                    yield thread

            ready, _, _ = select.select(self.threads, [], [])

        assert(False, "Unreachable code")


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

    Indexer(options).run()
