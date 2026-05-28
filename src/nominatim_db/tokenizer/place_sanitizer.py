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
from typing import Optional, List, Mapping, Sequence, Callable, Any, Tuple

from ..errors import UsageError
from ..config import Configuration
from .sanitizers.config import SanitizerConfig
from .sanitizers.base import SanitizerHandler, ProcessInfo
from ..data.place_name import PlaceName
from ..data.place_info import PlaceInfo


class PlaceSanitizer:
    """ Controller class which applies sanitizer functions on the place
        names and address before they are used by the token analysers.
    """

    def __init__(self, rules: Optional[Sequence[Mapping[str, Any]]],
                 config: Configuration) -> None:
        self.handlers: List[Callable[[ProcessInfo], None]] = []

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

    def process_names(self, place: PlaceInfo) -> Tuple[List[PlaceName], List[PlaceName]]:
        """ Extract a sanitized list of names and address parts from the
            given place. The function returns a tuple
            (list of names, list of address names)
        """
        obj = ProcessInfo(place)

        for func in self.handlers:
            func(obj)

        return obj.names, obj.address


def load_sanitizers(config: Configuration) -> PlaceSanitizer:
    """ Load the sanitizers from the configuration.

        This looks for a configuration file 'sanitizers.yaml' and creates
        a sanitizer based on that.

        Failing to find the file it will further look for the 'icu_tokenizer.yam;'
        and read sanitizers from there. This is only for backward compatibility
        and will go away in the next major version.
    """
    try:
        config.find_config_file('sanitizers.yaml')
        use_config = 'sanitizers.yaml'
    except UsageError:
        use_config = 'icu_tokenizer.yaml'

    rules = config.load_sub_configuration(use_config)

    if use_config == 'icu_tokenizer.yaml':
        rules = rules.get('sanitizers', [])

    return PlaceSanitizer(rules, config)
