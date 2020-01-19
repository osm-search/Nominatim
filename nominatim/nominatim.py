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

class IndexingThread(object):

    def __init__(self, thread_num, options):
        log.debug("Creating thread {}".format(thread_num))
        self.thread_num = thread_num
        self.conn = make_connection(options, asynchronous=True)
        self.wait()

        self.cursor = self.conn.cursor()
        self.perform("SET lc_messages TO 'C'")
        self.wait()

        self.current_query = None

    def wait(self):
        wait_select(self.conn)
        self.current_query = None

    def perform(self, sql, args=None):
        self.current_query = sql
        self.cursor.execute(sql, args)

    def is_done(self):
        if self.current_query is None:
            return True

        try:
            if self.conn.poll() == psycopg2.extensions.POLL_OK:
                self.current_query = None
                return True
        except psycopg2.extensions.TransactionRollbackError as e:
            if e.pgcode is None:
                raise RuntimeError("Postgres exception has no error code")
            if e.pgcode == '40P01':
                log.info("Deadlock detected, retry.")
                self.cursor.execute(sql)
            else:
                raise



class Indexer(object):

    def __init__(self, options):
        self.options = options
        self.conn = make_connection(options)

        self.threads = []
        self.poll = select.poll()
        for i in range(options.threads):
            t = IndexingThread(i, options)
            self.threads.append(t)
            self.poll.register(t.conn.fileno(), select.EPOLLIN)
        self.next_thread = 0

    def run(self):
        log.info("Starting indexing rank ({} to {}) using {} threads".format(
                 self.options.minrank, self.options.maxrank,
                 self.options.threads))

        for rank in range(self.options.minrank, 30):
            self.index(RankRunner(rank))

        if self.options.maxrank >= 30:
            self.index(InterpolationRunner())
            self.index(RankRunner(30))

    def index(self, obj):
        log.info("Starting {}".format(obj.name()))

        cur = self.conn.cursor(name="main")
        cur.execute(obj.sql_index_sectors())

        total_tuples = 0
        for r in cur:
            total_tuples += r[1]
        log.debug("Total number of rows; {}".format(total_tuples))

        cur.scroll(0, mode='absolute')

        done_tuples = 0
        rank_start_time = datetime.now()
        for r in cur:
            sector = r[0]

            # Should we do the remaining ones together?
            do_all = total_tuples - done_tuples < len(self.threads) * 1000

            pcur = self.conn.cursor(name='places')

            if do_all:
                pcur.execute(obj.sql_nosector_places())
            else:
                pcur.execute(obj.sql_sector_places(), (sector, ))

            for place in pcur:
                place_id = place[0]
                log.debug("Processing place {}".format(place_id))
                thread = self.find_free_thread()

                thread.perform(obj.sql_index_place(), (place_id,))
                done_tuples += 1

            pcur.close()

            if do_all:
                break

        cur.close()

        for t in self.threads:
            t.wait()

        rank_end_time = datetime.now()
        diff_seconds = (rank_end_time-rank_start_time).total_seconds()

        log.info("Done {} in {} @ {} per second - FINISHED {}\n".format(
                 done_tuples, int(diff_seconds),
                 done_tuples/diff_seconds, obj.name()))

    def find_free_thread(self):
        while True:
            for t in self.threads:
                if t.is_done():
                    return t

            self.poll.poll()

        assert(False, "Unreachable code")

class RankRunner(object):

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
                  WHERE indexed_status > 0 and geometry_sector = %s
                  ORDER BY geometry_sector"""

    def sql_index_place(self):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id = %s"


class InterpolationRunner(object):

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


def nominatim_arg_parser():
    """ Setup the command-line parser for the tool.
    """
    def h(s):
        return re.sub("\s\s+" , " ", s)

    p = ArgumentParser(description=__doc__,
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
