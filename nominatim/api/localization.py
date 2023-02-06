# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions for localizing names of results.
"""
from typing import Mapping, List, Optional

import re

class Locales:
    """ Helper class for localization of names.

        It takes a list of language prefixes in their order of preferred
        usage.
    """

    def __init__(self, langs: Optional[List[str]] = None):
        self.languages = langs or []
        self.name_tags: List[str] = []

        # Build the list of supported tags. It is currently hard-coded.
        self._add_lang_tags('name')
        self._add_tags('name', 'brand')
        self._add_lang_tags('official_name', 'short_name')
        self._add_tags('official_name', 'short_name', 'ref')


    def __bool__(self) -> bool:
        return len(self.languages) > 0


    def _add_tags(self, *tags: str) -> None:
        for tag in tags:
            self.name_tags.append(tag)
            self.name_tags.append(f"_place_{tag}")


    def _add_lang_tags(self, *tags: str) -> None:
        for tag in tags:
            for lang in self.languages:
                self.name_tags.append(f"{tag}:{lang}")
                self.name_tags.append(f"_place_{tag}:{lang}")


    def display_name(self, names: Optional[Mapping[str, str]]) -> str:
        """ Return the best matching name from a dictionary of names
            containing different name variants.

            If 'names' is null or empty, an empty string is returned. If no
            appropriate localization is found, the first name is returned.
        """
        if not names:
            return ''

        if len(names) > 1:
            for tag in self.name_tags:
                if tag in names:
                    return names[tag]

        # Nothing? Return any of the other names as a default.
        return next(iter(names.values()))


    @staticmethod
    def from_accept_languages(langstr: str) -> 'Locales':
        """ Create a localization object from a language list in the
            format of HTTP accept-languages header.

            The functions tries to be forgiving of format errors by first splitting
            the string into comma-separated parts and then parsing each
            description separately. Badly formatted parts are then ignored.
        """
        # split string into languages
        candidates = []
        for desc in langstr.split(','):
            m = re.fullmatch(r'\s*([a-z_-]+)(?:;\s*q\s*=\s*([01](?:\.\d+)?))?\s*',
                             desc, flags=re.I)
            if m:
                candidates.append((m[1], float(m[2] or 1.0)))

        # sort the results by the weight of each language (preserving order).
        candidates.sort(reverse=True, key=lambda e: e[1])

        # If a language has a region variant, also add the language without
        # variant but only if it isn't already in the list to not mess up the weight.
        languages = []
        for lid, _ in candidates:
            languages.append(lid)
            parts = lid.split('-', 1)
            if len(parts) > 1 and all(c[0] != parts[0] for c in candidates):
                languages.append(parts[0])

        return Locales(languages)
