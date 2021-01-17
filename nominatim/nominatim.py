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
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import logging
import sys
import getpass

from indexer.indexer import Indexer

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
    OPTIONS = nominatim_arg_parser().parse_args(sys.argv[1:])

    logging.basicConfig(stream=sys.stderr, format='%(levelname)s: %(message)s',
                        level=max(3 - OPTIONS.loglevel, 0) * 10)

    OPTIONS.password = None
    if OPTIONS.password_prompt:
        PASSWORD = getpass.getpass("Database password: ")
        OPTIONS.password = PASSWORD

    if OPTIONS.boundary_only:
        Indexer(OPTIONS).index_boundaries()
    else:
        Indexer(OPTIONS).index_by_rank()
