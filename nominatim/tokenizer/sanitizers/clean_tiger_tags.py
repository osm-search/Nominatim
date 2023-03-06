# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Sanitizer that preprocesses tags from the TIGER import.

It makes the following changes:

* remove state reference from tiger:county
"""
from typing import Callable
import re

from nominatim.tokenizer.sanitizers.base import ProcessInfo
from nominatim.tokenizer.sanitizers.config import SanitizerConfig

COUNTY_MATCH = re.compile('(.*), [A-Z][A-Z]')

def _clean_tiger_county(obj: ProcessInfo) -> None:
    """ Remove the state reference from tiger:county tags.

        This transforms a name like 'Hamilton, AL' into 'Hamilton'.
        If no state reference is detected at the end, the name is left as is.
    """
    if not obj.address:
        return

    for item in obj.address:
        if item.kind == 'tiger' and item.suffix == 'county':
            m = COUNTY_MATCH.fullmatch(item.name)
            if m:
                item.name = m[1]
            # Switch kind and suffix, the split left them reversed.
            item.kind = 'county'
            item.suffix = 'tiger'

            return


def create(_: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """ Create a function that preprocesses tags from the TIGER import.
    """
    return _clean_tiger_county
