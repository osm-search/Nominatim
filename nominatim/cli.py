"""
Command-line interface to the Nominatim functions for import, update,
database administration and querying.
"""
import sys
import os
import argparse
import logging
from pathlib import Path

from .config import Configuration
from .admin.exec_utils import run_legacy_script

from .indexer.indexer import Indexer

def _num_system_cpus():
    try:
        cpus = len(os.sched_getaffinity(0))
    except NotImplementedError:
        cpus = None

    return cpus or os.cpu_count()


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
        args = self.parser.parse_args()

        if args.subcommand is None:
            return self.parser.print_help()

        for arg in ('module_dir', 'osm2pgsql_path', 'phplib_dir', 'data_dir'):
            setattr(args, arg, Path(kwargs[arg]))
        args.project_dir = Path(args.project_dir)

        logging.basicConfig(stream=sys.stderr,
                            format='%(asctime)s: %(message)s',
                            datefmt='%Y-%m-%d %H:%M:%S',
                            level=max(4 - args.verbose, 1) * 10)

        args.config = Configuration(args.project_dir, args.data_dir / 'settings')

        return args.command.run(args)

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
                           type=argparse.FileType('w', encoding='UTF-8'),
                           help="""File to write the preprocessed phrases to.
                                   If omitted, it will be written to stdout.""")

    @staticmethod
    def run(args):
        if args.output.name != '<stdout>':
            raise NotImplementedError('Only output to stdout is currently implemented.')
        return run_legacy_script('specialphrases.php', '--wiki-import', nominatim_env=args)


class UpdateReplication:
    """\
    Update the database using an online replication service.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Arguments for initialisation')
        group.add_argument('--init', action='store_true',
                           help='Initialise the update process')
        group.add_argument('--no-update-functions', dest='update_functions',
                           action='store_false',
                           help="""Do not update the trigger function to
                                   support differential updates.""")
        group = parser.add_argument_group('Arguments for updates')
        group.add_argument('--check-for-updates', action='store_true',
                           help='Check if new updates are available and exit')
        group.add_argument('--once', action='store_true',
                           help="""Download and apply updates only once. When
                                   not set, updates are continuously applied""")
        group.add_argument('--no-index', action='store_false', dest='do_index',
                           help="""Do not index the new data. Only applicable
                                   together with --once""")

    @staticmethod
    def run(args):
        params = ['update.php']
        if args.init:
            params.append('--init-updates')
            if not args.update_functions:
                params.append('--no-update-functions')
        elif args.check_for_updates:
            params.append('--check-for-updates')
        else:
            if args.once:
                params.append('--import-osmosis')
            else:
                params.append('--import-osmosis-all')
            if not args.do_index:
                params.append('--no-index')

        return run_legacy_script(*params, nominatim_env=args)


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


class UpdateIndex:
    """\
    Reindex all new and modified data.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Filter arguments')
        group.add_argument('--boundaries-only', action='store_true',
                           help="""Index only administrative boundaries.""")
        group.add_argument('--no-boundaries', action='store_true',
                           help="""Index everything except administrative boundaries.""")
        group.add_argument('--minrank', '-r', type=int, metavar='RANK', default=0,
                           help='Minimum/starting rank')
        group.add_argument('--maxrank', '-R', type=int, metavar='RANK', default=30,
                           help='Maximum/finishing rank')

    @staticmethod
    def run(args):
        indexer = Indexer(args.config.get_libpq_dsn(),
                          args.threads or _num_system_cpus() or 1)

        if not args.no_boundaries:
            indexer.index_boundaries(args.minrank, args.maxrank)
        if not args.boundaries_only:
            indexer.index_by_rank(args.minrank, args.maxrank)

        if not args.no_boundaries and not args.boundaries_only:
            indexer.update_status_table()

        return 0


class UpdateRefresh:
    """\
    Recompute auxiliary data used by the indexing process.

    These functions must not be run in parallel with other update commands.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Data arguments')
        group.add_argument('--postcodes', action='store_true',
                           help='Update postcode centroid table')
        group.add_argument('--word-counts', action='store_true',
                           help='Compute frequency of full-word search terms')
        group.add_argument('--address-levels', action='store_true',
                           help='Reimport address level configuration')
        group.add_argument('--functions', action='store_true',
                           help='Update the PL/pgSQL functions in the database')
        group.add_argument('--wiki-data', action='store_true',
                           help='Update Wikipedia/data importance numbers.')
        group.add_argument('--importance', action='store_true',
                           help='Recompute place importances (expensive!)')
        group.add_argument('--website', action='store_true',
                           help='Refresh the directory that serves the scripts for the web API')
        group = parser.add_argument_group('Arguments for function refresh')
        group.add_argument('--no-diff-updates', action='store_false', dest='diffs',
                           help='Do not enable code for propagating updates')
        group.add_argument('--enable-debug-statements', action='store_true',
                           help='Enable debug warning statements in functions')

    @staticmethod
    def run(args):
        if args.postcodes:
            run_legacy_script('update.php', '--calculate-postcodes',
                              nominatim_env=args, throw_on_fail=True)
        if args.word_counts:
            run_legacy_script('update.php', '--recompute-word-counts',
                              nominatim_env=args, throw_on_fail=True)
        if args.address_levels:
            run_legacy_script('update.php', '--update-address-levels',
                              nominatim_env=args, throw_on_fail=True)
        if args.functions:
            params = ['setup.php', '--create-functions', '--create-partition-functions']
            if args.diffs:
                params.append('--enable-diff-updates')
            if args.enable_debug_statements:
                params.append('--enable-debug-statements')
            run_legacy_script(*params, nominatim_env=args, throw_on_fail=True)
        if args.wiki_data:
            run_legacy_script('setup.php', '--import-wikipedia-articles',
                              nominatim_env=args, throw_on_fail=True)
        # Attention: importance MUST come after wiki data import.
        if args.importance:
            run_legacy_script('update.php', '--recompute-importance',
                              nominatim_env=args, throw_on_fail=True)
        if args.website:
            run_legacy_script('setup.php', '--setup-website',
                              nominatim_env=args, throw_on_fail=True)


class AdminCheckDatabase:
    """\
    Check that the database is complete and operational.
    """

    @staticmethod
    def add_args(parser):
        pass # No options

    @staticmethod
    def run(args):
        return run_legacy_script('check_import_finished.php', nominatim_env=args)


class AdminWarm:
    """\
    Warm database caches for search and reverse queries.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Target arguments')
        group.add_argument('--search-only', action='store_const', dest='target',
                           const='search',
                           help="Only pre-warm tables for search queries")
        group.add_argument('--reverse-only', action='store_const', dest='target',
                           const='reverse',
                           help="Only pre-warm tables for reverse queries")

    @staticmethod
    def run(args):
        params = ['warm.php']
        if args.target == 'reverse':
            params.append('--reverse-only')
        if args.target == 'search':
            params.append('--search-only')
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

class QueryTodo:
    """\
    Todo
    """
    @staticmethod
    def add_args(parser):
        pass

    @staticmethod
    def run(args): # pylint: disable=W0613
        print("TODO: searching")


def nominatim(**kwargs):
    """\
    Command-line tools for importing, updating, administrating and
    querying the Nominatim database.
    """
    parser = CommandlineParser('nominatim', nominatim.__doc__)

    parser.add_subcommand('import', SetupAll)
    parser.add_subcommand('freeze', SetupFreeze)
    parser.add_subcommand('replication', UpdateReplication)

    parser.add_subcommand('check-database', AdminCheckDatabase)
    parser.add_subcommand('warm', AdminWarm)

    parser.add_subcommand('special-phrases', SetupSpecialPhrases)

    parser.add_subcommand('add-data', UpdateAddData)
    parser.add_subcommand('index', UpdateIndex)
    parser.add_subcommand('refresh', UpdateRefresh)

    parser.add_subcommand('export', QueryExport)

    if kwargs.get('phpcgi_path'):
        parser.add_subcommand('search', QueryTodo)
        parser.add_subcommand('reverse', QueryTodo)
        parser.add_subcommand('lookup', QueryTodo)
        parser.add_subcommand('details', QueryTodo)
        parser.add_subcommand('status', QueryTodo)
    else:
        parser.parser.epilog = 'php-cgi not found. Query commands not available.'

    return parser.run(**kwargs)
