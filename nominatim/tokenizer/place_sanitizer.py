# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Handler for cleaning name and address tags in place information before it
is handed to the token analysis.
"""
from typing import Optional, List, Mapping, Sequence, Callable, Any, Tuple

from nominatim.errors import UsageError
from nominatim.config import Configuration
from nominatim.tokenizer.sanitizers.config import SanitizerConfig
from nominatim.tokenizer.sanitizers.base import SanitizerHandler, ProcessInfo
from nominatim.data.place_name import PlaceName
from nominatim.data.place_info import PlaceInfo


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

                module: SanitizerHandler = \
                    config.load_plugin_module(func['step'], 'nominatim.tokenizer.sanitizers')

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
