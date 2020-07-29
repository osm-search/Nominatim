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
import psycopg2
from psycopg2.extras import wait_select
import select

from indexer.progress import ProgressLogger

log = logging.getLogger()

def make_connection(options, asynchronous=False):
    params = {'dbname' : options.dbname,
              'user' : options.user,
              'password' : options.password,
              'host' : options.host,
              'port' : options.port,
              'async' : asynchronous}

    return psycopg2.connect(**params)


class RankRunner(object):
    """ Returns SQL commands for indexing one rank within the placex table.
    """

    def __init__(self, rank):
        self.rank = rank

    def name(self):
        return "rank {}".format(self.rank)

    def sql_count_objects(self):
        return """SELECT count(*) FROM placex
                  WHERE rank_search = {} and indexed_status > 0
               """.format(self.rank)

    def sql_get_objects(self):
        return """SELECT place_id FROM placex
                  WHERE indexed_status > 0 and rank_search = {}
                  ORDER BY geometry_sector""".format(self.rank)

    def sql_index_place(self):
        return "UPDATE placex SET indexed_status = 0 WHERE place_id = %s"


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

    def sql_index_place(self):
        return """UPDATE location_property_osmline
                  SET indexed_status = 0 WHERE place_id = %s"""


class DBConnection(object):
    """ A single non-blocking database connection.
    """

    def __init__(self, options):
        self.current_query = None
        self.current_params = None

        self.conn = None
        self.connect()

    def connect(self):
        if self.conn is not None:
            self.cursor.close()
            self.conn.close()

        self.conn = make_connection(options, asynchronous=True)
        self.wait()

        self.cursor = self.conn.cursor()
        # Disable JIT and parallel workers as they are known to cause problems.
        # Update pg_settings instead of using SET because it does not yield
        # errors on older versions of Postgres where the settings are not
        # implemented.
        self.perform(
            """ UPDATE pg_settings SET setting = -1 WHERE name = 'jit_above_cost';
                UPDATE pg_settings SET setting = 0 
                   WHERE name = 'max_parallel_workers_per_gather';""")
        self.wait()

    def wait(self):
        """ Block until any pending operation is done.
        """
        while True:
            try:
                wait_select(self.conn)
                self.current_query = None
                return
            except psycopg2.extensions.TransactionRollbackError as e:
                if e.pgcode == '40P01':
                    log.info("Deadlock detected (params = {}), retry."
                              .format(self.current_params))
                    self.cursor.execute(self.current_query, self.current_params)
                else:
                    raise
            except psycopg2.errors.DeadlockDetected:
                self.cursor.execute(self.current_query, self.current_params)

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
                log.info("Deadlock detected (params = {}), retry.".format(self.current_params))
                self.cursor.execute(self.current_query, self.current_params)
            else:
                raise
        except psycopg2.errors.DeadlockDetected:
            self.cursor.execute(self.current_query, self.current_params)

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

        self.index(RankRunner(self.maxrank))

    def index(self, obj):
        """ Index a single rank or table. `obj` describes the SQL to use
            for indexing.
        """
        log.warning("Starting {}".format(obj.name()))

        cur = self.conn.cursor()
        cur.execute(obj.sql_count_objects())

        total_tuples = cur.fetchone()[0]
        log.debug("Total number of rows: {}".format(total_tuples))

        cur.close()

        next_thread = self.find_free_thread()
        progress = ProgressLogger(obj.name(), total_tuples)

        cur = self.conn.cursor(name='places')
        cur.execute(obj.sql_get_objects())

        for place in cur:
            place_id = place[0]
            log.debug("Processing place {}".format(place_id))
            thread = next(next_thread)

            thread.perform(obj.sql_index_place(), (place_id,))
            progress.add()

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
