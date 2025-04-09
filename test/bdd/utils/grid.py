# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
A grid describing node placement in an area.
Useful for visually describing geometries.
"""


class Grid:

    def __init__(self, table, step, origin):
        if step is None:
            step = 0.00001
        if origin is None:
            origin = (0.0, 0.0)
        self.grid = {}

        y = origin[1]
        for line in table:
            x = origin[0]
            for pt_id in line:
                if pt_id:
                    self.grid[pt_id] = (x, y)
                x += step
            y += step

    def get(self, nodeid):
        """ Get the coordinates for the given grid node.
        """
        return self.grid.get(nodeid)

    def parse_point(self, value):
        """ Get the coordinates for either a grid node or a full coordinate.
        """
        value = value.strip()
        if ' ' in value:
            return [float(v) for v in value.split(' ', 1)]

        return self.grid.get(value)

    def parse_line(self, value):
        return [self.parse_point(p) for p in value.split(',')]
