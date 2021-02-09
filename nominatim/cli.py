"""
Command-line interface to the Nominatim functions for import, update,
database administration and querying.
"""
import logging
import os
import sys
import argparse
from pathlib import Path

from .config import Configuration
from .tools.exec_utils import run_legacy_script, run_php_server
from .errors import UsageError
from . import clicmd

LOG = logging.getLogger()


class CommandlineParser:
    """ Wraps some of the common functions for parsing the command line
        and setting up subcommands.
    """
    def __init__(self, prog, description):
        self.parser = argparse.ArgumentParser(
            prog=prog,
            description=description,
            formatter_class=argparse.RawDescriptionHelpFormatter)

        self.subs = self.parser.add_subparsers(title='available commands',
                                               dest='subcommand')

        # Arguments added to every sub-command
        self.default_args = argparse.ArgumentParser(add_help=False)
        group = self.default_args.add_argument_group('Default arguments')
        group.add_argument('-h', '--help', action='help',
                           help='Show this help message and exit')
        group.add_argument('-q', '--quiet', action='store_const', const=0,
                           dest='verbose', default=1,
                           help='Print only error messages')
        group.add_argument('-v', '--verbose', action='count', default=1,
                           help='Increase verboseness of output')
        group.add_argument('--project-dir', metavar='DIR', default='.',
                           help='Base directory of the Nominatim installation (default:.)')
        group.add_argument('-j', '--threads', metavar='NUM', type=int,
                           help='Number of parallel threads to use')


    def add_subcommand(self, name, cmd):
        """ Add a subcommand to the parser. The subcommand must be a class
            with a function add_args() that adds the parameters for the
            subcommand and a run() function that executes the command.
        """
        parser = self.subs.add_parser(name, parents=[self.default_args],
                                      help=cmd.__doc__.split('\n', 1)[0],
                                      description=cmd.__doc__,
                                      formatter_class=argparse.RawDescriptionHelpFormatter,
                                      add_help=False)
        parser.set_defaults(command=cmd)
        cmd.add_args(parser)

    def run(self, **kwargs):
        """ Parse the command line arguments of the program and execute the
            appropriate subcommand.
        """
        args = self.parser.parse_args(args=kwargs.get('cli_args'))

        if args.subcommand is None:
            self.parser.print_help()
            return 1

        for arg in ('module_dir', 'osm2pgsql_path', 'phplib_dir', 'sqllib_dir',
                    'data_dir', 'config_dir', 'phpcgi_path'):
            setattr(args, arg, Path(kwargs[arg]))
        args.project_dir = Path(args.project_dir).resolve()

        logging.basicConfig(stream=sys.stderr,
                            format='%(asctime)s: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=max(4 - args.verbose, 1) * 10)

        args.config = Configuration(args.project_dir, args.config_dir)

        log = logging.getLogger()
        log.warning('Using project directory: %s', str(args.project_dir))

        try:
            return args.command.run(args)
        except UsageError as exception:
            if log.isEnabledFor(logging.DEBUG):
                raise # use Python's exception printing
            log.fatal('FATAL: %s', exception)

        # If we get here, then execution has failed in some way.
        return 1


##### Subcommand classes
#
# Each class needs to implement two functions: add_args() adds the CLI parameters
# for the subfunction, run() executes the subcommand.
#
# The class documentation doubles as the help text for the command. The
# first line is also used in the summary when calling the program without
# a subcommand.
#
# No need to document the functions each time.
# pylint: disable=C0111
# Using non-top-level imports to make pyosmium optional for replication only.
# pylint: disable=E0012,C0415


class SetupAll:
    """\
    Create a new Nominatim database from an OSM file.
    """

    @staticmethod
    def add_args(parser):
        group_name = parser.add_argument_group('Required arguments')
        group = group_name.add_mutually_exclusive_group(required=True)
        group.add_argument('--osm-file',
                           help='OSM file to be imported.')
        group.add_argument('--continue', dest='continue_at',
                           choices=['load-data', 'indexing', 'db-postprocess'],
                           help='Continue an import that was interrupted')
        group = parser.add_argument_group('Optional arguments')
        group.add_argument('--osm2pgsql-cache', metavar='SIZE', type=int,
                           help='Size of cache to be used by osm2pgsql (in MB)')
        group.add_argument('--reverse-only', action='store_true',
                           help='Do not create tables and indexes for searching')
        group.add_argument('--enable-debug-statements', action='store_true',
                           help='Include debug warning statements in SQL code')
        group.add_argument('--no-partitions', action='store_true',
                           help="""Do not partition search indices
                                   (speeds up import of single country extracts)""")
        group.add_argument('--no-updates', action='store_true',
                           help="""Do not keep tables that are only needed for
                                   updating the database later""")
        group = parser.add_argument_group('Expert options')
        group.add_argument('--ignore-errors', action='store_true',
                           help='Continue import even when errors in SQL are present')
        group.add_argument('--index-noanalyse', action='store_true',
                           help='Do not perform analyse operations during index')


    @staticmethod
    def run(args):
        params = ['setup.php']
        if args.osm_file:
            params.extend(('--all', '--osm-file', args.osm_file))
        else:
            if args.continue_at == 'load-data':
                params.append('--load-data')
            if args.continue_at in ('load-data', 'indexing'):
                params.append('--index')
            params.extend(('--create-search-indices', '--create-country-names',
                           '--setup-website'))
        if args.osm2pgsql_cache:
            params.extend(('--osm2pgsql-cache', args.osm2pgsql_cache))
        if args.reverse_only:
            params.append('--reverse-only')
        if args.enable_debug_statements:
            params.append('--enable-debug-statements')
        if args.no_partitions:
            params.append('--no-partitions')
        if args.no_updates:
            params.append('--drop')
        if args.ignore_errors:
            params.append('--ignore-errors')
        if args.index_noanalyse:
            params.append('--index-noanalyse')

        return run_legacy_script(*params, nominatim_env=args)


class SetupFreeze:
    """\
    Make database read-only.

    About half of data in the Nominatim database is kept only to be able to
    keep the data up-to-date with new changes made in OpenStreetMap. This
    command drops all this data and only keeps the part needed for geocoding
    itself.

    This command has the same effect as the `--no-updates` option for imports.
    """

    @staticmethod
    def add_args(parser):
        pass # No options

    @staticmethod
    def run(args):
        return run_legacy_script('setup.php', '--drop', nominatim_env=args)


class SetupSpecialPhrases:
    """\
    Maintain special phrases.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Input arguments')
        group.add_argument('--from-wiki', action='store_true',
                           help='Pull special phrases from the OSM wiki.')
        group = parser.add_argument_group('Output arguments')
        group.add_argument('-o', '--output', default='-',
                           help="""File to write the preprocessed phrases to.
                                   If omitted, it will be written to stdout.""")

    @staticmethod
    def run(args):
        if args.output != '-':
            raise NotImplementedError('Only output to stdout is currently implemented.')
        return run_legacy_script('specialphrases.php', '--wiki-import', nominatim_env=args)


class UpdateAddData:
    """\
    Add additional data from a file or an online source.

    Data is only imported, not indexed. You need to call `nominatim-update index`
    to complete the process.
    """

    @staticmethod
    def add_args(parser):
        group_name = parser.add_argument_group('Source')
        group = group_name.add_mutually_exclusive_group(required=True)
        group.add_argument('--file', metavar='FILE',
                           help='Import data from an OSM file')
        group.add_argument('--diff', metavar='FILE',
                           help='Import data from an OSM diff file')
        group.add_argument('--node', metavar='ID', type=int,
                           help='Import a single node from the API')
        group.add_argument('--way', metavar='ID', type=int,
                           help='Import a single way from the API')
        group.add_argument('--relation', metavar='ID', type=int,
                           help='Import a single relation from the API')
        group.add_argument('--tiger-data', metavar='DIR',
                           help='Add housenumbers from the US TIGER census database.')
        group = parser.add_argument_group('Extra arguments')
        group.add_argument('--use-main-api', action='store_true',
                           help='Use OSM API instead of Overpass to download objects')

    @staticmethod
    def run(args):
        if args.tiger_data:
            os.environ['NOMINATIM_TIGER_DATA_PATH'] = args.tiger_data
            return run_legacy_script('setup.php', '--import-tiger-data', nominatim_env=args)

        params = ['update.php']
        if args.file:
            params.extend(('--import-file', args.file))
        elif args.diff:
            params.extend(('--import-diff', args.diff))
        elif args.node:
            params.extend(('--import-node', args.node))
        elif args.way:
            params.extend(('--import-way', args.way))
        elif args.relation:
            params.extend(('--import-relation', args.relation))
        if args.use_main_api:
            params.append('--use-main-api')
        return run_legacy_script(*params, nominatim_env=args)


class QueryExport:
    """\
    Export addresses as CSV file from the database.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Output arguments')
        group.add_argument('--output-type', default='street',
                           choices=('continent', 'country', 'state', 'county',
                                    'city', 'suburb', 'street', 'path'),
                           help='Type of places to output (default: street)')
        group.add_argument('--output-format',
                           default='street;suburb;city;county;state;country',
                           help="""Semicolon-separated list of address types
                                   (see --output-type). Multiple ranks can be
                                   merged into one column by simply using a
                                   comma-separated list.""")
        group.add_argument('--output-all-postcodes', action='store_true',
                           help="""List all postcodes for address instead of
                                   just the most likely one""")
        group.add_argument('--language',
                           help="""Preferred language for output
                                   (use local name, if omitted)""")
        group = parser.add_argument_group('Filter arguments')
        group.add_argument('--restrict-to-country', metavar='COUNTRY_CODE',
                           help='Export only objects within country')
        group.add_argument('--restrict-to-osm-node', metavar='ID', type=int,
                           help='Export only children of this OSM node')
        group.add_argument('--restrict-to-osm-way', metavar='ID', type=int,
                           help='Export only children of this OSM way')
        group.add_argument('--restrict-to-osm-relation', metavar='ID', type=int,
                           help='Export only children of this OSM relation')


    @staticmethod
    def run(args):
        params = ['export.php',
                  '--output-type', args.output_type,
                  '--output-format', args.output_format]
        if args.output_all_postcodes:
            params.append('--output-all-postcodes')
        if args.language:
            params.extend(('--language', args.language))
        if args.restrict_to_country:
            params.extend(('--restrict-to-country', args.restrict_to_country))
        if args.restrict_to_osm_node:
            params.extend(('--restrict-to-osm-node', args.restrict_to_osm_node))
        if args.restrict_to_osm_way:
            params.extend(('--restrict-to-osm-way', args.restrict_to_osm_way))
        if args.restrict_to_osm_relation:
            params.extend(('--restrict-to-osm-relation', args.restrict_to_osm_relation))

        return run_legacy_script(*params, nominatim_env=args)


class AdminServe:
    """\
    Start a simple web server for serving the API.

    This command starts the built-in PHP webserver to serve the website
    from the current project directory. This webserver is only suitable
    for testing and develop. Do not use it in production setups!

    By the default, the webserver can be accessed at: http://127.0.0.1:8088
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Server arguments')
        group.add_argument('--server', default='127.0.0.1:8088',
                           help='The address the server will listen to.')

    @staticmethod
    def run(args):
        run_php_server(args.server, args.project_dir / 'website')


def nominatim(**kwargs):
    """\
    Command-line tools for importing, updating, administrating and
    querying the Nominatim database.
    """
    parser = CommandlineParser('nominatim', nominatim.__doc__)

    parser.add_subcommand('import', SetupAll)
    parser.add_subcommand('freeze', SetupFreeze)
    parser.add_subcommand('replication', clicmd.UpdateReplication)

    parser.add_subcommand('special-phrases', SetupSpecialPhrases)

    parser.add_subcommand('add-data', UpdateAddData)
    parser.add_subcommand('index', clicmd.UpdateIndex)
    parser.add_subcommand('refresh', clicmd.UpdateRefresh)

    parser.add_subcommand('admin', clicmd.AdminFuncs)

    parser.add_subcommand('export', QueryExport)
    parser.add_subcommand('serve', AdminServe)

    if kwargs.get('phpcgi_path'):
        parser.add_subcommand('search', clicmd.APISearch)
        parser.add_subcommand('reverse', clicmd.APIReverse)
        parser.add_subcommand('lookup', clicmd.APILookup)
        parser.add_subcommand('details', clicmd.APIDetails)
        parser.add_subcommand('status', clicmd.APIStatus)
    else:
        parser.parser.epilog = 'php-cgi not found. Query commands not available.'

    return parser.run(**kwargs)
