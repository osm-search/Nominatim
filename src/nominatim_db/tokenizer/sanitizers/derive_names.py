# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
This sanitizer can create additional name variants based on existing
names.

Arguments:
    type: Define which type of names should be considered for removal:
          proper names of the object ('name') or names defining the address
          ('address'). (default: 'name')

    filter-kind: Define which 'kind' of names are affected.
                 Takes a string or list of strings where each
                 string is a regular expression. A name is considered
                 to be a candidate for removal if its 'kind' property
                 fully matches any of the given regular expressions.
                 (default: no filter)

    filter-suffix: Restrict sanitizer to names with certain 'suffix' properties.
                   Takes a string or list of strings where each
                   string is a regular expression. A tag is considered to be a
                   candidate for removal if its 'suffix' property fully
                   matches any of the given regular expressions.
                   (default: no filter)

    filter-country: Restrict sanitizer to given countries. Takes a string or
                    list of strings where each string is a two-letter
                    lower-case country code.
                    (default: no filter)

    filter-rank: Define the address rank of places whose names should be
                 considered. Takes a string or list of strings
                 where each string is a number or range of number or the
                 form <from>-<to>.
                 See https://nominatim.org/release-docs/latest/customize/Ranking/#address-rank
                 to learn more about address rank.
                 (default: no filter)

    name-pattern: Regular expression to match the name proper against. Replacements
                  will only be made when the full name matches against this expression.
                  The expression may contain capture expressions which can
                  be used in the variant expression below.

    variants: Single string or list of strings of new variants to be created.
              The string may contain numbered backreferences, e.g. `\1`.

    keep-original: When set to true, the original name will be kept. Otherwise
                   the original is discarded when it matched the pattern.
                   (default: true)
"""
from typing import Callable, Optional

from ...data.place_name import PlaceName, PlaceNames
from .base import ProcessInfo
from .config import SanitizerConfig
from ._derived_name_sanitizer import DerivedNameSanitizer


class _NameSanitizer(DerivedNameSanitizer):

    def __init__(self, config: SanitizerConfig) -> None:
        super().__init__(config, keep_original=config.get_bool('keep-original', True))
        self.pattern = config.get_pattern('name-pattern')
        self.replacements = config.get_string_list('variants')

    def compute_derived_names(self, name: PlaceName, obj: ProcessInfo) -> Optional[PlaceNames]:
        if (m := self.pattern.fullmatch(name.name)) is not None:
            return [name.clone(name=n) for n in set(m.expand(r) for r in self.replacements)]

        return None


def create(config: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """ Create a function to process removal of certain names.
    """

    return _NameSanitizer(config)
