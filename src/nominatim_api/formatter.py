# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Name formatter for user-readable results
"""
from typing import List

from .localization import Locales
from .results import AddressLines, BaseResultT


class Formatter:
    """ Helper class for localization of names.

        It takes a list of language prefixes in their order of preferred
        usage.
    """

    def localize(self, lines: AddressLines, locales: Locales) -> None:
        """ Set the local name of address parts according to the chosen
            locale. Return the list of local names without duplicates.

            Only address parts that are marked as isaddress are localized.

            AddressLines should be modified in place.
        """
        for line in lines:
            if line.isaddress and line.names:
                line.local_name = locales.display_name(line.names)

    def localize_results(self, results: List[BaseResultT], locales: Locales) -> None:
        """ Set the local name of results according to the chosen
            locale. Return the list of local names without duplicates.
        """
        for result in results:
            result.locale_name = locales.display_name(result.names)
            if result.address_rows:
                self.localize(result.address_rows, locales)
