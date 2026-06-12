# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Base class for sanitizers that derive new place names from existing ones.
"""
from typing import Sequence, Optional
from abc import ABC, abstractmethod

from ...data.place_name import PlaceName, PlaceNames
from .base import ProcessInfo
from .config import SanitizerConfig
from ...errors import UsageError


def _to_rank(rstr: str) -> int:
    if not rstr.isdecimal():
        raise UsageError(f"Invalid rank parameter '{rstr}', must be a number.")

    rint = int(rstr)

    if rint < 0 or rint > 30:
        raise UsageError(f"Rank parameter '{rstr}' out of range. Must be between 0 and 30.")

    return rint


def _make_rank_set(ranks: Sequence[str]) -> set[int]:
    """ Parses the rank descriptions and returns a set of permissible ranks.
    """
    allowed_ranks = set()

    for rank in ranks:
        parts = [_to_rank(x) for x in rank.split('-')]

        if len(parts) == 1:
            allowed_ranks.add(parts[0])
        elif len(parts) == 2:
            allowed_ranks.update(range(parts[0], parts[1] + 1))
        else:
            raise UsageError(f"Rank parameter '{rank}' is not a value or range.")

    return allowed_ranks


class DerivedNameSanitizer(ABC):
    """ Abstract sanitizer class for sanitizers that add new place names
        based on the existing ones. The class provides basic filter
        configuration to restrict the names affected:

        * type (name vs. address)
        * kind (single value or list of regexes to match against kind)
        * suffix (single value or list of regexes to match against kind)
        * country_code: string or list of two-letter country codes
        * rank_address: string or list of ranks or rank ranges

        Further more, it can be configured if the original name should
        be kept.

        If a place name is deemed relevant, calls the handler function
        which must then return a list of derived place name objects.
    """

    def __init__(self, config: SanitizerConfig, keep_original: bool = True,
                 filter_kind_option: str = 'filter-kind',
                 filter_country_option: str = 'filter-country',
                 filter_suffix_option: str = 'filter-suffix',
                 filter_rank_option: str = 'filter-rank') -> None:
        self.type = config.get('type', 'name')
        self.filter_kind = config.get_filter(filter_kind_option)
        self.country_codes = config.get_string_list(filter_country_option) \
            if filter_country_option in config else None
        self.filter_suffix = config.get_filter(filter_suffix_option)
        self.allowed_ranks = _make_rank_set(config.get_string_list(filter_rank_option, ["0-30"]))
        self.keep_original = keep_original

    def __call__(self, obj: ProcessInfo) -> None:
        names = obj.names if self.type == 'name' else obj.address

        if names \
           and obj.place.rank_address in self.allowed_ranks\
           and (self.country_codes is None
                or obj.place.country_code in self.country_codes):
            filtered_names: PlaceNames = []

            for name in names:
                keep_name = True
                if self.filter_kind(name.kind) and self.filter_suffix(name.suffix or ''):
                    if (new_names := self.compute_derived_names(name, obj)) is not None:
                        filtered_names.extend(new_names)
                        keep_name = self.keep_original
                if keep_name:
                    filtered_names.append(name)

            if self.type == 'name':
                obj.names = filtered_names
            else:
                obj.address = filtered_names

    @abstractmethod
    def compute_derived_names(self, name: PlaceName,
                              obj: ProcessInfo) -> Optional[PlaceNames]:
        """ Filter function to be implemented by derived classes.
            Computes one or more derived names from the given name. The
            full object is handed in for references.

            Return None if the name should not be processed by the sanitizer.
            Otherwise return a list of place names that either replace the
            original one or are added, depending on the setting of 'keep_original'.
        """
        return None
