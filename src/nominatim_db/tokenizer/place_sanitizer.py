# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Handler for cleaning name and address tags in place information before it
is handed to the token analysis.
"""
from typing import Optional, Mapping, Sequence, Callable, Any, Dict

from ..errors import UsageError
from ..config import Configuration
from .sanitizers.config import SanitizerConfig
from .sanitizers.base import SanitizerHandler, ProcessInfo
from ..data.place_info import PlaceInfo


class PlaceSanitizer:
    """ Controller class which applies sanitizer functions on the place
        names and address before they are used by the token analysers.
    """

    def __init__(self, rules: Optional[Sequence[Mapping[str, Any]]],
                 config: Configuration,
                 country_rules: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None) -> None:
        self.handlers: list[Callable[[ProcessInfo], None]] = []
        self._country_handlers: Dict[str, list[Callable[[ProcessInfo], None]]] = {}

        if rules:
            for func in rules:
                if 'step' not in func:
                    raise UsageError("Sanitizer rule is missing the 'step' attribute.")
                if not isinstance(func['step'], str):
                    raise UsageError("'step' attribute must be a simple string.")
                if func['step'].startswith('_'):
                    raise UsageError("Illegal name for 'step', must not start with '_'.")
                if func['step'].startswith('_') or func['step'] in ('base', 'config'):
                    raise UsageError("'base' and 'config' cannot be used as name for 'step'.")

                module: SanitizerHandler = \
                    config.load_plugin_module(func['step'], 'nominatim_db.tokenizer.sanitizers')

                self.handlers.append(module.create(SanitizerConfig(func)))

        if country_rules:
            for country, country_rules_list in country_rules.items():
                if not country_rules_list:
                    continue
                handlers: list[Callable[[ProcessInfo], None]] = []
                for func in country_rules_list:
                    if 'step' not in func:
                        raise UsageError(
                            "Sanitizer rule in country configuration is missing "
                            "the 'step' attribute.")
                    if not isinstance(func['step'], str):
                        raise UsageError("'step' attribute must be a simple string.")
                    if func['step'].startswith('_'):
                        raise UsageError(
                            "Illegal name for 'step', must not start with '_'.")
                    if func['step'] in ('base', 'config'):
                        raise UsageError(
                            "'base' and 'config' cannot be used as name for 'step'.")

                    country_module: SanitizerHandler = \
                        config.load_plugin_module(func['step'],
                                                  'nominatim_db.tokenizer.sanitizers')

                    handlers.append(country_module.create(SanitizerConfig(func)))
                self._country_handlers[country] = handlers

    def process_names(self, place: PlaceInfo) -> None:
        """ Extract a sanitized list of names and address parts from the
            given place. The function returns a tuple
            (list of names, list of address names)
        """
        obj = ProcessInfo(place)

        for func in self.handlers:
            func(obj)

        if place.country_code and place.country_code in self._country_handlers:
            for func in self._country_handlers[place.country_code]:
                func(obj)

        place.set_sanitized(obj.names, obj.address)


def load_sanitizers(config: Configuration) -> PlaceSanitizer:
    """ Load the sanitizers from the configuration.

        This looks for a configuration file 'sanitizers.yaml' and creates
        a sanitizer based on that.

        Failing to find the file it will further look for the 'icu_tokenizer.yaml'
        and read sanitizers from there. This is only for backward compatibility
        and will go away in the next major version.

        Additionally loads country-specific sanitizers from the country
        settings configuration.
    """
    if config.config_file_exists('sanitizers.yaml'):
        rules = config.load_sub_configuration('sanitizers.yaml')
    else:
        rules = config.load_sub_configuration('icu_tokenizer.yaml')\
                      .get('sanitizers', [])

    country_rules: Dict[str, Sequence[Mapping[str, Any]]] = {}
    country_config = config.load_sub_configuration('country_settings.yaml')
    for code, props in country_config.items():
        if 'sanitizers' in props:
            country_rules[code] = props['sanitizers']

    return PlaceSanitizer(rules, config, country_rules)
