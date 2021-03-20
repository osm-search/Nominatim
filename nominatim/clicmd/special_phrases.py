"""
    Implementation of the 'import-special-phrases' command.
"""
import logging
from nominatim.tools.special_phrases import import_from_wiki
from nominatim.db.connection import connect

LOG = logging.getLogger()

# Do not repeat documentation of subcommand classes.
# pylint: disable=C0111

class ImportSpecialPhrases:
    """\
    Import special phrases.
    """
    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Input arguments')
        group.add_argument('--from-wiki', action='store_true',
                           help='Import special phrases from the OSM wiki to the database.')

    @staticmethod
    def run(args):
        if args.from_wiki:
            LOG.warning('Special phrases importation starting')
            with connect(args.config.get_libpq_dsn()) as db_connection:
                import_from_wiki(args.config, db_connection)
        return 0
