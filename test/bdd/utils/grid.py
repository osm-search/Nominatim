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
import re


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

    def geometry_to_wkt(self, value):
        """ Parses the given value into a geometry and returns the WKT.

            The value can either be a WKT already or a geometry shortcut
            with coordinates or grid points.
        """
        if re.fullmatch(r'([A-Z]+)\((.*)\)', value) is not None:
            return value  # already a WKT

        # points
        if ',' not in value:
            x, y = self.parse_point(value)
            return f"POINT({x} {y})"

        # linestring
        if '(' not in value:
            coords = ','.join(' '.join(f"{p:.7f}" for p in pt)
                              for pt in self.parse_line(value))
            return f"LINESTRING({coords})"

        # simple polygons
        coords = ','.join(' '.join(f"{p:.7f}" for p in pt)
                          for pt in self.parse_line(value[1:-1]))
        return f"POLYGON(({coords}))"
