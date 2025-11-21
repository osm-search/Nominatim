# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing and managing static country information.
"""
from typing import Dict, Any, Iterable, Tuple, Optional, List, overload

from ..config import Configuration


class _CountryInfo:
    """ Caches country-specific properties from the configuration file.
    """

    def __init__(self) -> None:
        self._info: Dict[str, Dict[str, Any]] = {}

    def load(self, config: Configuration) -> None:
        """ Load the country languages from the configuration files,
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


def get(country: str) -> Dict[str, Any]:
    """ Get country information for the country with the given country code. """
    return _COUNTRY_INFO._info.get(country) or {}


def get_lang(country: str) -> List[str]:
    """ Get country languages for the country with the given country code."""
    country_info = _COUNTRY_INFO._info.get(country.lower(), {})
    languages = country_info.get('languages', [])
    return languages if isinstance(languages, list) else []


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
