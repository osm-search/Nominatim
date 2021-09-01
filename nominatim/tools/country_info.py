"""
Functions for importing and managing static country information.
"""
import psycopg2.extras
import yaml

from nominatim.db import utils as db_utils
from nominatim.db.connection import connect

class _CountryInfo:
    """ Caches country-specific properties from the configuration file.
    """

    def __init__(self):
        self._info = {}

    def load(self, configfile):
        if not self._info:
            self._info = yaml.safe_load(configfile.read_text())

    def items(self):
        return self._info.items()


_COUNTRY_INFO = _CountryInfo()

def setup_country_config(configfile):
    """ Load country properties from the configuration file.
        Needs to be called before using any other functions in this
        file.
    """
    _COUNTRY_INFO.load(configfile)
    print(_COUNTRY_INFO._info)


def setup_country_tables(dsn, sql_dir, ignore_partitions=False):
    """ Create and populate the tables with basic static data that provides
        the background for geocoding. Data is assumed to not yet exist.
    """
    db_utils.execute_file(dsn, sql_dir / 'country_name.sql')
    db_utils.execute_file(dsn, sql_dir / 'country_osm_grid.sql.gz')

    params = []
    for ccode, props in _COUNTRY_INFO.items():
        if ccode is not None and props is not None:
            if ignore_partitions:
                partition = 0
            else:
                partition = props.get('partition')
            if ',' in (props.get('languages', ',') or ','):
                lang = None
            else:
                lang = props['languages']
            params.append((ccode, partition, lang))

    with connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute_values(
                """ UPDATE country_name
                    SET partition = part, country_default_language_code = lang
                    FROM (VALUES %s) AS v (cc, part, lang)
                    WHERE country_code = v.cc""", params)
        conn.commit()


def create_country_names(conn, tokenizer, languages=None):
    """ Add default country names to search index. `languages` is a comma-
        separated list of language codes as used in OSM. If `languages` is not
        empty then only name translations for the given languages are added
        to the index.
    """
    if languages:
        languages = languages.split(',')

    def _include_key(key):
        return key == 'name' or \
               (key.startswith('name:') and (not languages or key[5:] in languages))

    with conn.cursor() as cur:
        psycopg2.extras.register_hstore(cur)
        cur.execute("""SELECT country_code, name FROM country_name
                       WHERE country_code is not null""")

        with tokenizer.name_analyzer() as analyzer:
            for code, name in cur:
                names = {'countrycode': code}
                if code == 'gb':
                    names['short_name'] = 'UK'
                if code == 'us':
                    names['short_name'] = 'United States'

                # country names (only in languages as provided)
                if name:
                    names.update(((k, v) for k, v in name.items() if _include_key(k)))

                analyzer.add_country_names(code, names)

    conn.commit()
