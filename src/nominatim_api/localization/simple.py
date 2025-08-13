# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
from typing import List
import re
from .base import Locales
from ..results import AddressLines, BaseResultT


class SimpleLocales(Locales):
    """ Simple Helper class for localization of names.

        It takes a list of language prefixes in their order of preferred
        usage.
    """

    def localize(self, lines: AddressLines) -> None:
        """ Sets the local name of address parts according to the chosen
            locale.

            Only address parts that are marked as isaddress are localized.

            AddressLines should be modified in place.
        """
        for line in lines:
            if line.isaddress and line.names:
                line.local_name = self.display_name(line.names)

    def localize_results(self, results: List[BaseResultT]) -> None:
        """ Set the local name of results according to the chosen
            locale.
        """
        for result in results:
            result.locale_name = self.display_name(result.names)
            if result.address_rows:
                self.localize(result.address_rows)

    @staticmethod
    def from_accept_languages(langstr: str) -> 'SimpleLocales':
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

        return SimpleLocales(languages)
