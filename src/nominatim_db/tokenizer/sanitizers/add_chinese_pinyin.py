# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
For the places which only have a Han character name,
add a Pinyin transliteration as an extra name.
This allows users who type iin Pinyin to still find
the places which are only tagged in Chinese script.
"""
from typing import Callable
import unicodedata

from .base import ProcessInfo
from .config import SanitizerConfig
from ...data.place_name import PlaceName

def _is_han(text: str) -> bool:
    """ Check if the text contains any CJK unified ideograph characters.
    """
    return any(unicodedata.name(c, '').startswith('CJK UNIFIED IDEOGRAPH')
               for c in text)

def create(_: SanitizerConfig) -> Callable[[ProcessInfo], None]:
    """ Create a sanitizer that adds Pinyin variants for Han character names.
    """
    try:
        from icu import Transliterator
        han_to_pinyin = Transliterator.createInstance('Han-Latin')
        ascii_trans = Transliterator.createInstance('Latin-ASCII')
    except Exception:
        return lambda _: None

    def _process(obj: ProcessInfo) -> None:
        """ For each Han character name without a Pinyin variant,
            add a Pinyin transliteration as an additional name.
        """
        if not obj.names:
            return

        # Collect suffixes that already have a Pinyin/Latin name
        existing_suffixes = set()
        for name in obj.names:
            if name.suffix and not _is_han(name.name):
                existing_suffixes.add(name.suffix)
            if not name.suffix and not _is_han(name.name):
                existing_suffixes.add(None)

        new_names = []
        for name in obj.names:
            if not _is_han(name.name):
                continue
            # Only add Pinyin if no Latin version exists for this suffix
            if name.suffix not in existing_suffixes:
                pinyin = ascii_trans.transliterate(
                            han_to_pinyin.transliterate(name.name)).strip().lower()
                if pinyin:
                    new_names.append(name.clone(name=pinyin))

        obj.names.extend(new_names)

    return _process