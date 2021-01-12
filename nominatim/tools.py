"""
Command-line interface to the Nominatim functions for import, update,
database administration and querying.
"""
import sys
import argparse
import logging

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
        group.add_argument('--project-dir', metavar='DIR',
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

    def run(self):
        """ Parse the command line arguments of the program and execute the
            appropriate subcommand.
        """
        args = self.parser.parse_args()

        if args.subcommand is None:
            self.parser.print_help()
        else:
            logging.basicConfig(stream=sys.stderr,
                                format='%(asctime)s %(levelname)s: %(message)s',
                                datefmt='%Y-%m-%d %H:%M:%S',
                                level=max(4 - args.verbose, 1) * 10)
            args.command.run(args)


class SetupAll:
    """\
    Create a new database and import data from an OSM file.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Required arguments')
        group.add_argument('--osm-file', required=True,
                           help='OSM file to be imported.')
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
        group.add_argument('--disable-token-precalc', action='store_true',
                           help='Disable name precalculation')
        group.add_argument('--index-noanalyse', action='store_true',
                           help='Do not perform analyse operations during index')


    @staticmethod
    def run(args):
        print("TODO: setup all", args)


class SetupContinue:
    """\
    Continue an import previously started with the `all` command.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Required aruments')
        group.add_argument('pickup-point', nargs=1,
                           choices=['load-data', 'indexing', 'db-postprocess'],
                           help='Position where to continue the import')

    @staticmethod
    def run(args):
        print("TODO: setup continue", args)

class SetupDrop:
    """\
    Remove all tables only needed for keeping data up-to-date.

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
        print("TODO: setup drop", args)

class SetupAddExternal:
    """\
    Add additional external data to the Nominatim database.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Data sources')
        group.add_argument('--tiger-data', metavar='DIR',
                           help='Add housenumbers from the US TIGER census database.')
        group.add_argument('--wiki-data',
                           help='Add or update Wikipedia/data importance numbers.')

    @staticmethod
    def run(args):
        print("TODO: setup extern", args)


class SetupSpecialPhrases:
    """\
    Create special phrases.
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
        print("./utils/specialphrases.php --from-wiki", args)


class UpdateStatus:
    """\
    Check for the status of the data.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Additional arguments')
        group.add_argument('--check-for-updates', action='store_true',
                           help='Check if new updates are available')


    @staticmethod
    def run(args):
        print('./utils/update.php --check-for-updates', args)


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
        group.add_argument('--once', action='store_true',
                           help="""Download and apply updates only once. When
                                   not set, updates are continuously applied""")
        group.add_argument('--no-index', action='store_false', dest='do_index',
                           help="""Do not index the new data. Only applicable
                                   together with --once""")

    @staticmethod
    def run(args):
        if args.init:
            print('./utils/update.php --init-updates', args)
        else:
            print('./utils/update.php --import-osmosis(-all)', args)


class UpdateImport:
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
        group = parser.add_argument_group('Extra arguments')
        group.add_argument('--use-main-api', action='store_true',
                           help='Use OSM API instead of Overpass to download objects')

    @staticmethod
    def run(args):
        print('./utils/update.php --import-*', args)


class UpdateIndex:
    """\
    Reindex all new and modified data.
    """

    @staticmethod
    def add_args(parser):
        pass

    @staticmethod
    def run(args):
        print('./utils/update.php --index', args)


class UpdateRefresh:
    """\
    Recompute auxillary data used by the indexing process.

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
        group.add_argument('--importance', action='store_true',
                           help='Recompute place importances')

    @staticmethod
    def run(args):
        print('./utils/update.php', args)



class AdminCreateFunctions:
    """\
    Update the PL/pgSQL functions in the database.
    """

    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Expert arguments')
        group.add_argument('--no-diff-updates', action='store_false', dest='diffs',
                           help='Do not enable code for propagating updates')

    @staticmethod
    def run(args):
        print("TODO: ./utils/setup.php --create-functions --enable-diff-updates "
              "--create-partition-functions", args)


class AdminSetupWebsite:
    """\
    Setup the directory that serves the scripts for the web API.

    The directory is created under `/website` in the project directory.
    """

    @staticmethod
    def add_args(parser):
        pass # No options

    @staticmethod
    def run(args):
        print("TODO: ./utils/setup.php --setup-website", args)


class AdminCheckDatabase:
    """\
    Check that the Nominatim database is complete and operational.
    """

    @staticmethod
    def add_args(parser):
        pass # No options

    @staticmethod
    def run(args):
        print("TODO: ./utils/check_import_finished.php", args)


class AdminWarm:
    """\
    Pre-warm caches of the database for search and reverse queries.
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
        print("TODO: ./utils/warm.php", args)


class AdminExport:
    """\
    Export addresses as CSV file from a Nominatim database
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
        print("TODO: ./utils/export.php", args)

def setup(**kwargs):
    """\
    Commands for creating a Nominatim database and importing data.
    """
    parser = CommandlineParser('nominatim-setup', setup.__doc__)

    parser.add_subcommand('all', SetupAll)
    parser.add_subcommand('continue', SetupContinue())
    parser.add_subcommand('drop', SetupDrop())
    parser.add_subcommand('add-external', SetupAddExternal())
    parser.add_subcommand('special-phrases', SetupSpecialPhrases())
    parser.run()

def update(**kwargs):
    """\
    Commands for updating data inside a Nominatim database.
    """
    parser = CommandlineParser('nominatim-update', update.__doc__)

    parser.add_subcommand('status', UpdateStatus())
    parser.add_subcommand('replication', UpdateReplication())
    parser.add_subcommand('import', UpdateImport())
    parser.add_subcommand('index', UpdateIndex())
    parser.add_subcommand('refresh', UpdateRefresh())

    parser.run()

def admin(**kwargs):
    """\
    Commands for inspecting and maintaining a Nomiantim database.
    """
    parser = CommandlineParser('nominatim-admin', admin.__doc__)

    parser.add_subcommand('create-functions', AdminCreateFunctions())
    parser.add_subcommand('setup-website', AdminSetupWebsite())
    parser.add_subcommand('check-database', AdminCheckDatabase())
    parser.add_subcommand('warm', AdminWarm())
    parser.add_subcommand('export', AdminExport())

    parser.run()

def query(**kwargs):
    """\
    Query the database.

    This provides a command-line query interface to Nominatim's API.
    """
    parser = CommandlineParser('nominatim-query', query.__doc__)

    parser.run()
