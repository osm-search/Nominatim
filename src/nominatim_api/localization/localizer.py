# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
from .base import AbstractLocales
from ..results import BaseResultT


class Locales(AbstractLocales):
    """ Simple Helper class for localization of names.

        It takes a list of language prefixes in their order of preferred
        usage.
    """

    def localize(self, result: BaseResultT) -> None:
        """ Sets the local name of address parts according to the chosen
            locale.

            Only address parts that are marked as isaddress are localized.

            AddressLines should be modified in place.
        """
        if not result.address_rows:
            return

        for line in result.address_rows:
            if line.isaddress and line.names:
                line.local_name = self.display_name(line.names)

    @staticmethod
    def from_accept_languages(langstr: str) -> 'Locales':
        """ Parse a language list in the format of HTTP accept-languages header.

            The function tries to be forgiving of format errors by first splitting
            the string into comma-separated parts and then parsing each
            description separately. Badly formatted parts are then ignored.
        """
        candidates = AbstractLocales.sort_languages(langstr)

        # If a language has a region variant, also add the language without
        # variant but only if it isn't already in the list to not mess up the weight.
        languages = []
        for lid, _ in candidates:
            languages.append(lid)
            parts = lid.split('-', 1)
            if len(parts) > 1 and all(c[0] != parts[0] for c in candidates):
                languages.append(parts[0])

        return Locales(languages)
