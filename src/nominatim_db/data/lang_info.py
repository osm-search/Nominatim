# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing and managing static language information.
"""
from typing import Dict, Any, Iterable, Tuple, Optional, overload

from ..config import Configuration


class _LangInfo:
    """ Caches language-specific properties from the configuration file.
    """

    def __init__(self) -> None:
        self._info: Dict[str, Dict[str, Any]] = {}

    def load(self, config: Configuration) -> None:
        """ Load the language properties from the configuration files,
            if they are not loaded yet.
        """
        if not self._info:
            self._info = config.load_sub_configuration('languages.yaml')

    def items(self) -> Iterable[Tuple[str, Dict[str, Any]]]:
        """ Return tuples of (country_code, property dict) as iterable.
        """
        return self._info.items()

    def get(self, lang: str) -> Dict[str, Any]:
        """ Get language information for the language with the given language code.
        """
        return self._info.get(lang, {})


_LANG_INFO = _LangInfo()


def setup_lang_config(config: Configuration) -> None:
    """ Load country properties from the configuration file.
        Needs to be called before using any other functions in this
        file.
    """
    _LANG_INFO.load(config)


@overload
def iterate() -> Iterable[Tuple[str, Dict[str, Any]]]:
    ...


@overload
def iterate(prop: str) -> Iterable[Tuple[str, Any]]:
    ...


def iterate(prop: Optional[str] = None) -> Iterable[Tuple[str, Dict[str, Any]]]:
    """ Iterate over languages and their properties.

        When `prop` is None, all countries are returned with their complete
        set of properties.

        If `prop` is given, then only countries are returned where the
        given property is set. The second item of the tuple contains only
        the content of the given property.
    """
    if prop is None:
        return _LANG_INFO.items()

    return ((c, p[prop]) for c, p in _LANG_INFO.items() if prop in p)
