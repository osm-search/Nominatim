# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for computation of centroids.
"""
from collections.abc import Collection

class PointsCentroid:
    """ Centroid computation from single points using an online algorithm.
        More points may be added at any time.

        Coordinates are internally treated as a 7-digit fixed-point float
        (i.e. in OSM style).
    """

    def __init__(self):
        self.sum_x = 0
        self.sum_y = 0
        self.count = 0

    def centroid(self):
        """ Return the centroid of all points collected so far.
        """
        if self.count == 0:
            raise ValueError("No points available for centroid.")

        return (float(self.sum_x/self.count)/10000000,
                float(self.sum_y/self.count)/10000000)


    def __len__(self):
        return self.count


    def __iadd__(self, other):
        if isinstance(other, Collection) and len(other) == 2:
            if all(isinstance(p, (float, int)) for p in other):
                x, y = other
                self.sum_x += int(x * 10000000)
                self.sum_y += int(y * 10000000)
                self.count += 1
                return self

        raise ValueError("Can only add 2-element tuples to centroid.")
