# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from ..results import AddressLines, BaseResultT
from ..config import Configuration
import re


class Locales(ABC):
    """Interface for localization logic."""
    def __init__(self, langs: Optional[List[str]] = None):
        self.config = Configuration(None)
        self.languages = langs or []
        self.name_tags: List[str] = []

        parts = self.config.OUTPUT_NAMES.split(',')

        for part in parts:
            part = part.strip()
            if part.endswith(":XX"):
                self._add_lang_tags(part[:-3])
            else:
                self._add_tags(part)

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

    def display_name(self, names: Optional[Dict[str, str]]) -> str:
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

    @abstractmethod
    def localize(self, lines: AddressLines) -> None:
        """ Localize address parts according to the chosen locale. """
        pass

    @abstractmethod
    def localize_results(self, results: List[BaseResultT]) -> None:
        """ Localize results according to the chosen locale. """
        pass

    @staticmethod
    def from_accept_languages(langstr: str) -> List[str]:
        """ Parse a language list in the format of HTTP accept-languages header.

            The function tries to be forgiving of format errors by first splitting
            the string into comma-separated parts and then parsing each
            description separately. Badly formatted parts are then ignored.
        """
        candidates = []
        for desc in langstr.split(','):
            m = re.fullmatch(r'\s*([a-z_-]+)(?:;\s*q\s*=\s*([01](?:\.\d+)?))?\s*',
                             desc, flags=re.I)
            if m:
                candidates.append((m[1], float(m[2] or 1.0)))

        # Sort the results by the weight of each language (preserving order).
        candidates.sort(reverse=True, key=lambda e: e[1])

        # If a language has a region variant, also add the language without
        # variant but only if it isn't already in the list to not mess up the weight.
        languages = []
        for lid, _ in candidates:
            languages.append(lid)
            parts = lid.split('-', 1)
            if len(parts) > 1 and all(c[0] != parts[0] for c in candidates):
                languages.append(parts[0])

        return languages
