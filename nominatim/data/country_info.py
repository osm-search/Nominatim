# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing and managing static country information.
"""
from typing import Dict, Any, Iterable, Tuple, Optional, Container, overload
from pathlib import Path
import psycopg2.extras

from nominatim.db import utils as db_utils
from nominatim.db.connection import connect, Connection
from nominatim.errors import UsageError
from nominatim.config import Configuration
from nominatim.tokenizer.base import AbstractTokenizer

def _flatten_name_list(names: Any) -> Dict[str, str]:
    if names is None:
        return {}

    if not isinstance(names, dict):
        raise UsageError("Expected key-value list for names in country_settings.py")

    flat = {}
    for prefix, remain in names.items():
        if isinstance(remain, str):
            flat[prefix] = remain
        elif not isinstance(remain, dict):
            raise UsageError("Entries in names must be key-value lists.")
        else:
            for suffix, name in remain.items():
                if suffix == 'default':
                    flat[prefix] = name
                else:
                    flat[f'{prefix}:{suffix}'] = name

    return flat



class _CountryInfo:
    """ Caches country-specific properties from the configuration file.
    """

    def __init__(self) -> None:
        self._info: Dict[str, Dict[str, Any]] = {}


    def load(self, config: Configuration) -> None:
        """ Load the country properties from the configuration files,
            if they are not loaded yet.
        """
        if not self._info:
            self._info = config.load_sub_configuration('country_settings.yaml')
            for prop in self._info.values():
                # Convert languages into a list for simpler handling.
                if 'languages' not in prop:
                    prop['languages'] = []
                elif not isinstance(prop['languages'], list):
                    prop['languages'] = [x.strip()
                                         for x in prop['languages'].split(',')]
                prop['names'] = _flatten_name_list(prop.get('names'))


    def items(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        """ Return tuples of (country_code, property dict) as iterable.
        """
        return self._info.items()

    def get(self, country_code: str) -> Dict[str, Any]:
        """ Get country information for the country with the given country code.
        """
        return self._info.get(country_code, {})



_COUNTRY_INFO = _CountryInfo()


def setup_country_config(config: Configuration) -> None:
    """ Load country properties from the configuration file.
        Needs to be called before using any other functions in this
        file.
    """
    _COUNTRY_INFO.load(config)

@overload
def iterate() -> Iterable[Tuple[str, Dict[str, Any]]]:
    ...

@overload
def iterate(prop: str) -> Iterable[Tuple[str, Any]]:
    ...

def iterate(prop: Optional[str] = None) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """ Iterate over country code and properties.

        When `prop` is None, all countries are returned with their complete
        set of properties.

        If `prop` is given, then only countries are returned where the
        given property is set. The second item of the tuple contains only
        the content of the given property.
    """
    if prop is None:
        return _COUNTRY_INFO.items()

    return ((c, p[prop]) for c, p in _COUNTRY_INFO.items() if prop in p)


def setup_country_tables(dsn: str, sql_dir: Path, ignore_partitions: bool = False) -> None:
    """ Create and populate the tables with basic static data that provides
        the background for geocoding. Data is assumed to not yet exist.
    """
    db_utils.execute_file(dsn, sql_dir / 'country_osm_grid.sql.gz')

    params = []
    for ccode, props in _COUNTRY_INFO.items():
        if ccode is not None and props is not None:
            if ignore_partitions:
                partition = 0
            else:
                partition = props.get('partition', 0)
            lang = props['languages'][0] if len(
                props['languages']) == 1 else None

            params.append((ccode, props['names'], lang, partition))
    with connect(dsn) as conn:
        with conn.cursor() as cur:
            psycopg2.extras.register_hstore(cur)
            cur.execute(
                """ CREATE TABLE public.country_name (
                        country_code character varying(2),
                        name public.hstore,
                        derived_name public.hstore,
                        country_default_language_code text,
                        partition integer
                    ); """)
            cur.execute_values(
                """ INSERT INTO public.country_name
                    (country_code, name, country_default_language_code, partition) VALUES %s
                """, params)
        conn.commit()


def create_country_names(conn: Connection, tokenizer: AbstractTokenizer,
                         languages: Optional[Container[str]] = None) -> None:
    """ Add default country names to search index. `languages` is a comma-
        separated list of language codes as used in OSM. If `languages` is not
        empty then only name translations for the given languages are added
        to the index.
    """
    def _include_key(key: str) -> bool:
        return ':' not in key or not languages or \
               key[key.index(':') + 1:] in languages

    with conn.cursor() as cur:
        psycopg2.extras.register_hstore(cur)
        cur.execute("""SELECT country_code, name FROM country_name
                       WHERE country_code is not null""")

        with tokenizer.name_analyzer() as analyzer:
            for code, name in cur:
                names = {'countrycode': code}

                # country names (only in languages as provided)
                if name:
                    names.update({k : v for k, v in name.items() if _include_key(k)})

                analyzer.add_country_names(code, names)

    conn.commit()
