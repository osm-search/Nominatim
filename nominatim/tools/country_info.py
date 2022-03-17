# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing and managing static country information.
"""
import json
from io import StringIO
import psycopg2.extras

from nominatim.db import utils as db_utils
from nominatim.db.connection import connect

class _CountryInfo:
    """ Caches country-specific properties from the configuration file.
    """

    def __init__(self):
        self._info = {}


    def load(self, config):
        """ Load the country properties from the configuration files,
            if they are not loaded yet.
        """
        if not self._info:
            self._info = config.load_sub_configuration('country_settings.yaml')
            # Convert languages into a list for simpler handling.
            for prop in self._info.values():
                if 'languages' not in prop:
                    prop['languages'] = []
                elif not isinstance(prop['languages'], list):
                    prop['languages'] = [x.strip()
                                         for x in prop['languages'].split(',')]
                if 'names' not in prop:
                    prop['names']['name'] = {}

    def items(self):
        """ Return tuples of (country_code, property dict) as iterable.
        """
        return self._info.items()


_COUNTRY_INFO = _CountryInfo()

def setup_country_config(config):
    """ Load country properties from the configuration file.
        Needs to be called before using any other functions in this
        file.
    """
    _COUNTRY_INFO.load(config)


def iterate():
    """ Iterate over country code and properties.
    """
    return _COUNTRY_INFO.items()


def setup_country_tables(dsn, sql_dir, ignore_partitions=False):
    """ Create and populate the tables with basic static data that provides
        the background for geocoding. Data is assumed to not yet exist.
    """
    db_utils.execute_file(dsn, sql_dir / 'country_osm_grid.sql.gz')

    def add_prefix_to_keys(name, prefix):
        return {prefix+k: v for k, v in name.items()}

    params, country_names_data = [], ''
    for ccode, props in _COUNTRY_INFO.items():
        if ccode is not None and props is not None:
            if ignore_partitions:
                partition = 0
            else:
                partition = props.get('partition')
            lang = props['languages'][0] if len(props['languages']) == 1 else None
            params.append((ccode, partition, lang))

            name = add_prefix_to_keys(props.get('names').get('name'), 'name:')
            name = json.dumps(name , ensure_ascii=False, separators=(', ', '=>'))
            country_names_data += ccode + '\t' + name[1:-1] + '\n'
    with connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """ CREATE TABLE public.country_name (
                        country_code character varying(2),
                        name public.hstore,
                        derived_name public.hstore,
                        country_default_language_code text,
                        partition integer
                    ); """)
            data = StringIO(country_names_data)
            cur.copy_from(data, 'country_name', columns=('country_code', 'name'))
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
        return key.startswith('name:') and \
            key[5:] in languages or key[5:] == 'default'

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
