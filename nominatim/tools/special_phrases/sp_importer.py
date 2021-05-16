"""
    Module containing the class handling the import
    of the special phrases.

    Phrases are analyzed and imported into the database.

    The phrases already present in the database which are not
    valids anymore are removed.
"""
import logging
import os
from os.path import isfile
from pathlib import Path
import re
import subprocess
import json

from psycopg2.sql import Identifier, Literal, SQL
from nominatim.errors import UsageError
from nominatim.tools.special_phrases.importer_statistics import SpecialPhrasesImporterStatistics

LOG = logging.getLogger()
class SPImporter():
    # pylint: disable-msg=too-many-instance-attributes
    """
        Class handling the process of special phrases importations into the database.

        Take a sp loader which load the phrases from an external source.
    """
    def __init__(self, config, phplib_dir, db_connection, sp_loader) -> None:
        self.config = config
        self.phplib_dir = phplib_dir
        self.db_connection = db_connection
        self.sp_loader = sp_loader
        self.statistics_handler = SpecialPhrasesImporterStatistics()
        self.black_list, self.white_list = self._load_white_and_black_lists()
        self.sanity_check_pattern = re.compile(r'^\w+$')
        # This set will contain all existing phrases to be added.
        # It contains tuples with the following format: (lable, class, type, operator)
        self.word_phrases = set()
        #This set will contain all existing place_classtype tables which doesn't match any
        #special phrases class/type on the wiki.
        self.table_phrases_to_delete = set()

    def import_phrases(self, tokenizer):
        """
            Iterate through all specified languages and
            extract corresponding special phrases from the wiki.
        """
        LOG.warning('Special phrases importation starting')
        self._fetch_existing_place_classtype_tables()

        #Store pairs of class/type for further processing
        class_type_pairs = set()

        for loaded_phrases in self.sp_loader:
            for phrase in loaded_phrases:
                result = self._process_phrase(phrase)
                if result:
                    class_type_pairs.update(result)

        self._create_place_classtype_table_and_indexes(class_type_pairs)
        self._remove_non_existent_tables_from_db()
        self.db_connection.commit()

        with tokenizer.name_analyzer() as analyzer:
            analyzer.update_special_phrases(self.word_phrases)

        LOG.warning('Import done.')
        self.statistics_handler.notify_import_done()


    def _fetch_existing_place_classtype_tables(self):
        """
            Fetch existing place_classtype tables.
            Fill the table_phrases_to_delete set of the class.
        """
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema='public'
            AND table_name like 'place_classtype_%';
        """
        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL(query))
            for row in db_cursor:
                self.table_phrases_to_delete.add(row[0])

    def _load_white_and_black_lists(self):
        """
            Load white and black lists from phrases-settings.json.
        """
        settings_path = (self.config.config_dir / 'phrase-settings.json').resolve()

        if self.config.PHRASE_CONFIG:
            settings_path = self._convert_php_settings_if_needed(self.config.PHRASE_CONFIG)

        with settings_path.open("r") as json_settings:
            settings = json.load(json_settings)
        return settings['blackList'], settings['whiteList']

    def _check_sanity(self, phrase):
        """
            Check sanity of given inputs in case somebody added garbage in the wiki.
            If a bad class/type is detected the system will exit with an error.
        """
        class_matchs = self.sanity_check_pattern.findall(phrase.p_class)
        type_matchs = self.sanity_check_pattern.findall(phrase.p_type)

        if not class_matchs or not type_matchs:
            LOG.warning("Bad class/type: %s=%s. It will not be imported",
                        phrase.p_class, phrase.p_type)
            return False
        return True

    def _process_phrase(self, phrase):
        """
            Processes the given phrase by checking black and white list
            and sanity.
            Return the class/type pair corresponding to the phrase.
        """

        #blacklisting: disallow certain class/type combinations
        if phrase.p_class in self.black_list.keys() \
           and phrase.p_type in self.black_list[phrase.p_class]:
            return None

        #whitelisting: if class is in whitelist, allow only tags in the list
        if phrase.p_class in self.white_list.keys() \
           and phrase.p_type not in self.white_list[phrase.p_class]:
            return None

        #sanity check, in case somebody added garbage in the wiki
        if not self._check_sanity(phrase):
            self.statistics_handler.notify_one_phrase_invalid()
            return None

        self.word_phrases.add((phrase.p_label, phrase.p_class,
                               phrase.p_type, phrase.p_operator))

        return set({(phrase.p_class, phrase.p_type)})


    def _create_place_classtype_table_and_indexes(self, class_type_pairs):
        """
            Create table place_classtype for each given pair.
            Also create indexes on place_id and centroid.
        """
        LOG.warning('Create tables and indexes...')

        sql_tablespace = self.config.TABLESPACE_AUX_DATA
        if sql_tablespace:
            sql_tablespace = ' TABLESPACE '+sql_tablespace

        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute("CREATE INDEX idx_placex_classtype ON placex (class, type)")

        for pair in class_type_pairs:
            phrase_class = pair[0]
            phrase_type = pair[1]

            table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)

            if table_name in self.table_phrases_to_delete:
                self.statistics_handler.notify_one_table_ignored()
                #Remove this table from the ones to delete as it match a class/type
                #still existing on the special phrases of the wiki.
                self.table_phrases_to_delete.remove(table_name)
                #So dont need to create the table and indexes.
                continue

            #Table creation
            self._create_place_classtype_table(sql_tablespace, phrase_class, phrase_type)

            #Indexes creation
            self._create_place_classtype_indexes(sql_tablespace, phrase_class, phrase_type)

            #Grant access on read to the web user.
            self._grant_access_to_webuser(phrase_class, phrase_type)

            self.statistics_handler.notify_one_table_created()

        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute("DROP INDEX idx_placex_classtype")


    def _create_place_classtype_table(self, sql_tablespace, phrase_class, phrase_type):
        """
            Create table place_classtype of the given phrase_class/phrase_type if doesn't exit.
        """
        table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)
        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL("""
                    CREATE TABLE IF NOT EXISTS {{}} {} 
                    AS SELECT place_id AS place_id,st_centroid(geometry) AS centroid FROM placex 
                    WHERE class = {{}} AND type = {{}}""".format(sql_tablespace))
                              .format(Identifier(table_name), Literal(phrase_class),
                                      Literal(phrase_type)))


    def _create_place_classtype_indexes(self, sql_tablespace, phrase_class, phrase_type):
        """
            Create indexes on centroid and place_id for the place_classtype table.
        """
        index_prefix = 'idx_place_classtype_{}_{}_'.format(phrase_class, phrase_type)
        base_table = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)
        #Index on centroid
        if not self.db_connection.index_exists(index_prefix + 'centroid'):
            with self.db_connection.cursor() as db_cursor:
                db_cursor.execute(SQL("""
                    CREATE INDEX {{}} ON {{}} USING GIST (centroid) {}""".format(sql_tablespace))
                                  .format(Identifier(index_prefix + 'centroid'),
                                          Identifier(base_table)), sql_tablespace)

        #Index on place_id
        if not self.db_connection.index_exists(index_prefix + 'place_id'):
            with self.db_connection.cursor() as db_cursor:
                db_cursor.execute(SQL(
                    """CREATE INDEX {{}} ON {{}} USING btree(place_id) {}""".format(sql_tablespace))
                                  .format(Identifier(index_prefix + 'place_id'),
                                          Identifier(base_table)))


    def _grant_access_to_webuser(self, phrase_class, phrase_type):
        """
            Grant access on read to the table place_classtype for the webuser.
        """
        table_name = 'place_classtype_{}_{}'.format(phrase_class, phrase_type)
        with self.db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL("""GRANT SELECT ON {} TO {}""")
                              .format(Identifier(table_name),
                                      Identifier(self.config.DATABASE_WEBUSER)))

    def _remove_non_existent_tables_from_db(self):
        """
            Remove special phrases which doesn't exist on the wiki anymore.
            Delete the place_classtype tables.
        """
        LOG.warning('Cleaning database...')
        #Array containing all queries to execute. Contain tuples of format (query, parameters)
        queries_parameters = []

        #Delete place_classtype tables corresponding to class/type which are not on the wiki anymore
        for table in self.table_phrases_to_delete:
            self.statistics_handler.notify_one_table_deleted()
            query = SQL('DROP TABLE IF EXISTS {}').format(Identifier(table))
            queries_parameters.append((query, ()))

        with self.db_connection.cursor() as db_cursor:
            for query, parameters in queries_parameters:
                db_cursor.execute(query, parameters)

    def _convert_php_settings_if_needed(self, file_path):
        """
            Convert php settings file of special phrases to json file if it is still in php format.
        """
        if not isfile(file_path):
            raise UsageError(str(file_path) + ' is not a valid file.')

        file, extension = os.path.splitext(file_path)
        json_file_path = Path(file + '.json').resolve()

        if extension not in('.php', '.json'):
            raise UsageError('The custom NOMINATIM_PHRASE_CONFIG file has not a valid extension.')

        if extension == '.php' and not isfile(json_file_path):
            try:
                subprocess.run(['/usr/bin/env', 'php', '-Cq',
                                (self.phplib_dir / 'migration/PhraseSettingsToJson.php').resolve(),
                                file_path], check=True)
                LOG.warning('special_phrase configuration file has been converted to json.')
                return json_file_path
            except subprocess.CalledProcessError:
                LOG.error('Error while converting %s to json.', file_path)
                raise
        else:
            return json_file_path
