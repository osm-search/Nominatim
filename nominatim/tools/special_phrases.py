"""
    Functions to import special phrases into the database.
"""
import logging
import re
import sys
from psycopg2.sql import Identifier, Literal, SQL
from settings.phrase_settings import BLACK_LIST, WHITE_LIST
from nominatim.tools.exec_utils import get_url

LOG = logging.getLogger()

def import_from_wiki(config, db_connection, languages=None):
    """
        Iterate through all specified languages and
        extract corresponding special phrases from the wiki.
    """
    #Compile the match regex to increase performance for the following loop.
    occurence_pattern = re.compile(
        r'\| ([^\|]+) \|\| ([^\|]+) \|\| ([^\|]+) \|\| ([^\|]+) \|\| ([\-YN])'
    )
    sanity_check_pattern = re.compile(r'^\w+$')

    languages = _get_languages(config) if not languages else languages

    #array for pairs of class/type
    pairs = dict()
    for lang in languages:
        LOG.warning('Import phrases for lang: %s', lang)
        wiki_page_xml_content = _get_wiki_content(lang)
        #One match will be of format [label, class, type, operator, plural]
        matches = occurence_pattern.findall(wiki_page_xml_content)

        for match in matches:
            phrase_label = match[0].strip()
            phrase_class = match[1].strip()
            phrase_type = match[2].strip()
            phrase_operator = match[3].strip()
            #hack around a bug where building=yes was imported withq quotes into the wiki
            phrase_type = re.sub(r'\"|&quot;', '', phrase_type)

            #sanity check, in case somebody added garbage in the wiki
            _check_sanity(lang, phrase_class, phrase_type, sanity_check_pattern)

            #blacklisting: disallow certain class/type combinations
            if phrase_class in BLACK_LIST.keys() and phrase_type in BLACK_LIST[phrase_class]:
                continue
            #whitelisting: if class is in whitelist, allow only tags in the list
            if phrase_class in WHITE_LIST.keys() and phrase_type not in WHITE_LIST[phrase_class]:
                continue

            #add class/type to the pairs dict
            pairs[f'{phrase_class}|{phrase_type}'] = (phrase_class, phrase_type)

            _process_amenity(
                db_connection, phrase_label, phrase_class, phrase_type, phrase_operator
            )

    _create_place_classtype_table_and_indexes(db_connection, config, pairs)
    db_connection.commit()
    LOG.warning('Import done.')


def _get_languages(config):
    """
        Get list of all languages from env config file
        or default if there is no languages configured.
        The system will extract special phrases only from all specified languages.
    """
    default_languages = [
        'af', 'ar', 'br', 'ca', 'cs', 'de', 'en', 'es',
        'et', 'eu', 'fa', 'fi', 'fr', 'gl', 'hr', 'hu',
        'ia', 'is', 'it', 'ja', 'mk', 'nl', 'no', 'pl',
        'ps', 'pt', 'ru', 'sk', 'sl', 'sv', 'uk', 'vi']
    return config.LANGUAGES or default_languages


def _get_wiki_content(lang):
    """
        Request and return the wiki page's content
        corresponding to special phrases for a given lang.
        Requested URL Example :
            https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/EN
    """
    url = 'https://wiki.openstreetmap.org/wiki/Special:Export/Nominatim/Special_Phrases/' + lang.upper() # pylint: disable=line-too-long
    return get_url(url)


def _check_sanity(lang, phrase_class, phrase_type, pattern):
    """
        Check sanity of given inputs in case somebody added garbage in the wiki.
        If a bad class/type is detected the system will exit with an error.
    """
    try:
        if len(pattern.findall(phrase_class)) < 1 or len(pattern.findall(phrase_type)) < 1:
            sys.exit()
    except SystemExit:
        LOG.error("Bad class/type for language %s: %s=%s", lang, phrase_class, phrase_type)
        raise


def _process_amenity(db_connection, phrase_label, phrase_class, phrase_type, phrase_operator):
    """
        Add phrase lookup and corresponding class and type to the word table based on the operator.
    """
    with db_connection.cursor() as db_cursor:
        if phrase_operator == 'near':
            db_cursor.execute("""SELECT getorcreate_amenityoperator(
                              make_standard_name(%s), %s, %s, 'near')""",
                              (phrase_label, phrase_class, phrase_type))
        elif phrase_operator == 'in':
            db_cursor.execute("""SELECT getorcreate_amenityoperator(
                              make_standard_name(%s), %s, %s, 'in')""",
                              (phrase_label, phrase_class, phrase_type))
        else:
            db_cursor.execute("""SELECT getorcreate_amenity(
                              make_standard_name(%s), %s, %s)""",
                              (phrase_label, phrase_class, phrase_type))


def _create_place_classtype_table_and_indexes(db_connection, config, pairs):
    """
        Create table place_classtype for each given pair.
        Also create indexes on place_id and centroid.
    """
    LOG.warning('Create tables and indexes...')

    sql_tablespace = config.TABLESPACE_AUX_DATA
    if sql_tablespace:
        sql_tablespace = ' TABLESPACE '+sql_tablespace

    with db_connection.cursor() as db_cursor:
        db_cursor.execute("CREATE INDEX idx_placex_classtype ON placex (class, type)")

    for _, pair in pairs.items():
        phrase_class = pair[0]
        phrase_type = pair[1]

        #Table creation
        _create_place_classtype_table(
            db_connection, sql_tablespace, phrase_class, phrase_type
        )

        #Indexes creation
        _create_place_classtype_indexes(
            db_connection, sql_tablespace, phrase_class, phrase_type
        )

        #Grant access on read to the web user.
        _grant_access_to_webuser(
            db_connection, config, phrase_class, phrase_type
        )

    with db_connection.cursor() as db_cursor:
        db_cursor.execute("DROP INDEX idx_placex_classtype")


def _create_place_classtype_table(db_connection, sql_tablespace, phrase_class, phrase_type):
    """
        Create table place_classtype of the given phrase_class/phrase_type if doesn't exit.
    """
    with db_connection.cursor() as db_cursor:
        db_cursor.execute(SQL(f"""
                CREATE TABLE IF NOT EXISTS {{}} {sql_tablespace} 
                AS SELECT place_id AS place_id,st_centroid(geometry) AS centroid FROM placex 
                WHERE class = {{}} AND type = {{}}""")
                          .format(Identifier(f'place_classtype_{phrase_class}_{phrase_type}'),
                                  Literal(phrase_class), Literal(phrase_type)))


def _create_place_classtype_indexes(db_connection, sql_tablespace, phrase_class, phrase_type):
    """
        Create indexes on centroid and place_id for the place_classtype table.
    """
    #Index on centroid
    if not db_connection.index_exists(f'idx_place_classtype_{phrase_class}_{phrase_type}_centroid'):
        with db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL(f"""
                    CREATE INDEX {{}} ON {{}} USING GIST (centroid) {sql_tablespace}""")
                              .format(Identifier(
                                  f"""idx_place_classtype_{phrase_class}_{phrase_type}_centroid"""),
                                      Identifier(f'place_classtype_{phrase_class}_{phrase_type}')))

    #Index on place_id
    if not db_connection.index_exists(f'idx_place_classtype_{phrase_class}_{phrase_type}_place_id'):
        with db_connection.cursor() as db_cursor:
            db_cursor.execute(SQL(f"""
            CREATE INDEX {{}} ON {{}} USING btree(place_id) {sql_tablespace}""")
                              .format(Identifier(
                                  f"""idx_place_classtype_{phrase_class}_{phrase_type}_place_id"""),
                                      Identifier(f'place_classtype_{phrase_class}_{phrase_type}')))


def _grant_access_to_webuser(db_connection, config, phrase_class, phrase_type):
    """
        Grant access on read to the table place_classtype for the webuser.
    """
    with db_connection.cursor() as db_cursor:
        db_cursor.execute(SQL("""GRANT SELECT ON {} TO {}""")
                          .format(Identifier(f'place_classtype_{phrase_class}_{phrase_type}'),
                                  Identifier(config.DATABASE_WEBUSER)))
