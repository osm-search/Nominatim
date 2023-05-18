# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2023 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper function for parsing parameters and and outputting data
specifically for the v1 version of the API.
"""

REVERSE_MAX_RANKS = [2, 2, 2,   # 0-2   Continent/Sea
                     4, 4,      # 3-4   Country
                     8,         # 5     State
                     10, 10,    # 6-7   Region
                     12, 12,    # 8-9   County
                     16, 17,    # 10-11 City
                     18,        # 12    Town
                     19,        # 13    Village/Suburb
                     22,        # 14    Hamlet/Neighbourhood
                     25,        # 15    Localities
                     26,        # 16    Major Streets
                     27,        # 17    Minor Streets
                     30         # 18    Building
                    ]


def zoom_to_rank(zoom: int) -> int:
    """ Convert a zoom parameter into a rank according to the v1 API spec.
    """
    return REVERSE_MAX_RANKS[max(0, min(18, zoom))]
