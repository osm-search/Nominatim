# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
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

    Special phrases are search terms that narrow down the type of object
    that should be searched. For example, you might want to search for
    'Hotels in Barcelona'. The OSM wiki has a selection of special phrases
    in many languages, which can be imported with this command.

    You can also provide your own phrases in a CSV file. The file needs to have
    the following five columns:
     * phrase - the term expected for searching
     * class - the OSM tag key of the object type
     * type - the OSM tag value of the object type
     * operator - the kind of search to be done (one of: in, near, name, -)
     * plural - whether the term is a plural or not (Y/N)

    An example file can be found in the Nominatim sources at
    'test/testdb/full_en_phrases_test.csv'.

    The import can be further configured to ignore specific key/value pairs.
    This is particularly useful when importing phrases from the wiki. The
    default configuration excludes some very common tags like building=yes.
    The configuration can be customized by putting a file `phrase-settings.json`
    with custom rules into the project directory or by using the `--config`
    option to point to another configuration file.
    """
    @staticmethod
    def add_args(parser):
        group = parser.add_argument_group('Input arguments')
        group.add_argument('--import-from-wiki', action='store_true',
                           help='Import special phrases from the OSM wiki to the database')
        group.add_argument('--import-from-csv', metavar='FILE',
                           help='Import special phrases from a CSV file')
        group.add_argument('--no-replace', action='store_true',
                           help='Keep the old phrases and only add the new ones')
        group.add_argument('--config', action='store',
                           help='Configuration file for black/white listing '
                                '(default: phrase-settings.json)')

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
            sp loader and then start the import of special phrases.
        """
        from ..tokenizer import factory as tokenizer_factory

        tokenizer = tokenizer_factory.get_tokenizer_for_db(args.config)
        should_replace = not args.no_replace
        with connect(args.config.get_libpq_dsn()) as db_connection:
            SPImporter(
                args.config, db_connection, loader
            ).import_phrases(tokenizer, should_replace)
