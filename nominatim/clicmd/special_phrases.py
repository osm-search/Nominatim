"""
    Implementation of the 'special-phrases' command.
"""
import logging
from nominatim.errors import UsageError
from pathlib import Path
from nominatim.tools import SPWikiLoader
from nominatim.tools import SPImporter
from nominatim.db.connection import connect

LOG = logging.getLogger()

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111
# Using non-top-level imports to avoid eventually unused imports.
# pylint: disable=E0012,C0415

class ImportSpecialPhrases:
    """\
    Import special phrases.
    """
    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Input arguments')
        group.add_argument('--import-from-wiki', action='store_true',
                           help='Import special phrases from the OSM wiki to the database.')
        group.add_argument('--csv-file', metavar='FILE',
                    help='CSV file containing phrases to import.')

    @staticmethod
    def run(args):
        from ..tokenizer import factory as tokenizer_factory

        if args.import_from_wiki:
            tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
            with connect(args.config.get_libpq_dsn()) as db_connection:
                SPImporter(
                    args.config, args.phplib_dir, db_connection, SPWikiLoader(args.config)
                ).import_phrases(tokenizer)

        if args.csv_file:
            if not Path(args.csv_file).is_file():
                LOG.fatal("CSV file '%s' does not exist.", args.csv_file)
                raise UsageError('Cannot access file.')

        return 0
