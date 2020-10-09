#!/usr/bin/python3
# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim.
# Copyright (C) 2020 Sarah Hoffmann

"""
Script for analysing the indexing process.

The script enables detailed logging for nested statements and then
runs the indexing process for teh given object. Detailed 'EXPLAIN ANALYSE'
information is printed for each executed query in the trigger. The
transaction is then rolled back, so that no actual changes to the database
happen. It also disables logging into the system log, so that the
log files are not cluttered.
"""

from argparse import ArgumentParser, RawDescriptionHelpFormatter, ArgumentTypeError
import psycopg2
import getpass
import re

class Analyser(object):

    def __init__(self, options):
        password = None
        if options.password_prompt:
            password = getpass.getpass("Database password: ")

        self.options = options
        self.conn = psycopg2.connect(dbname=options.dbname,
                                     user=options.user,
                                     password=password,
                                     host=options.host,
                                     port=options.port)



    def run(self):
        c = self.conn.cursor()

        if self.options.placeid:
            place_id = self.options.placeid
        else:
            if self.options.rank:
                c.execute(f"""select place_id from placex
                              where rank_address = {self.options.rank}
                              and linked_place_id is null
                              limit 1""")
                objinfo = f"rank {self.options.rank}"

            if self.options.osmid:
                osm_type = self.options.osmid[0].upper()
                if osm_type not in ('N', 'W', 'R'):
                    raise RuntimeError("OSM ID must be of form <N|W|R><id>")
                try:
                    osm_id = int(self.options.osmid[1:])
                except ValueError:
                    raise RuntimeError("OSM ID must be of form <N|W|R><id>")

                c.execute(f"""SELECT place_id FROM placex
                              WHERE osm_type = '{osm_type}' AND osm_id = {osm_id}""")
                objinfo = f"OSM object {self.options.osmid}"


            if c.rowcount < 1:
                raise RuntimeError(f"Cannot find a place for {objinfo}.")
            place_id = c.fetchone()[0]

        c.execute(f"""update placex set indexed_status = 2 where
                      place_id = {place_id}""")

        c.execute("""SET auto_explain.log_min_duration = '0';
                     SET auto_explain.log_analyze = 'true';
                     SET auto_explain.log_nested_statements = 'true';
                     LOAD 'auto_explain';
                     SET client_min_messages = LOG;
                     SET log_min_messages = FATAL""");

        c.execute(f"""update placex set indexed_status = 0 where
                      place_id = {place_id}""")

        c.close() # automatic rollback

        for l in self.conn.notices:
            print(l)


if __name__ == '__main__':
    def h(s):
        return re.sub("\s\s+" , " ", s)

    p = ArgumentParser(description=__doc__,
                       formatter_class=RawDescriptionHelpFormatter)

    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument('--rank', dest='rank', type=int,
                       help='Analyse indexing of the given address rank')
    group.add_argument('--osm-id', dest='osmid', type=str,
                       help='Analyse indexing of the given OSM object')
    group.add_argument('--place-id', dest='placeid', type=int,
                       help='Analyse indexing of the given Nominatim object')
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

    Analyser(p.parse_args()).run()
