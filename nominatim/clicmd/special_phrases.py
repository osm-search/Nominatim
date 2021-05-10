"""
    Implementation of the 'special-phrases' command.
"""
import logging
from pathlib import Path
from nominatim.errors import UsageError
from nominatim.db.connection import connect
from nominatim.tools.special_phrases.sp_importer import SPImporter
from nominatim.tools.special_phrases.sp_wiki_loader import SPWikiLoader
from nominatim.tools.special_phrases.sp_csv_loader import SPCsvLoader

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
        group.add_argument('--import-from-csv', metavar='FILE',
                           help='Import special phrases from a CSV file.')

    @staticmethod
    def run(args):
        if args.import_from_wiki:
            ImportSpecialPhrases.start_import(args, SPWikiLoader(args.config))

        if args.import_from_csv:
            if not Path(args.import_from_csv).is_file():
                LOG.fatal("CSV file '%s' does not exist.", args.import_from_csv)
                raise UsageError('Cannot access file.')

            ImportSpecialPhrases.start_import(args, SPCsvLoader(args.import_from_csv))

        return 0

    @staticmethod
    def start_import(args, loader):
        """
            Create the SPImporter object containing the right
            SPLoader and then start the import of special phrases.
        """
        from ..tokenizer import factory as tokenizer_factory

        tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
        with connect(args.config.get_libpq_dsn()) as db_connection:
            SPImporter(
                args.config, args.phplib_dir, db_connection, loader
            ).import_phrases(tokenizer)
