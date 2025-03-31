# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper functions to compare expected values.
"""
import json
import re
import math
import itertools

from psycopg import sql as pysql
from psycopg.rows import dict_row, tuple_row
from .geometry_alias import ALIASES

COMPARATOR_TERMS = {
    'exactly': lambda exp, act: exp == act,
    'more than': lambda exp, act: act > exp,
    'less than': lambda exp, act: act < exp,
}


def _pretty(obj):
    return json.dumps(obj, sort_keys=True, indent=2)


def within_box(value, expect):
    coord = [float(x) for x in expect.split(',')]

    if isinstance(value, str):
        value = value.split(',')
    value = list(map(float, value))

    if len(value) == 2:
        return coord[0] <= value[0] <= coord[2] \
               and coord[1] <= value[1] <= coord[3]

    if len(value) == 4:
        return value[0] >= coord[0] and value[1] <= coord[1] \
               and value[2] >= coord[2] and value[3] <= coord[3]

    raise ValueError("Not a coordinate or bbox.")


COMPARISON_FUNCS = {
    None: lambda val, exp: str(val) == exp,
    'i': lambda val, exp: str(val).lower() == exp.lower(),
    'fm': lambda val, exp: re.fullmatch(exp, val) is not None,
    'dict': lambda val, exp: val is None if exp == '-' else (val == eval('{' + exp + '}')),
    'in_box': within_box
}

OSM_TYPE = {'node': 'n', 'way': 'w', 'relation': 'r',
            'N': 'n', 'W': 'w', 'R': 'r'}


class ResultAttr:
    """ Returns the given attribute as a string.

        The key parameter determines how the value is formatted before
        returning. To refer to sub attributes, use '+' to add more keys
        (e.g. 'name+ref' will access obj['name']['ref']). A '!' introduces
        a formatting suffix. If no suffix is given, the value will be
        converted using the str() function.

        Available formatters:

        !:...   - use a formatting expression according to Python Mini Format Spec
        !i      - make case-insensitive comparison
        !fm     - consider comparison string a regular expression and match full value
        !wkt    - convert the expected value to a WKT string before comparing
        !in_box - the expected value is a comma-separated bbox description
    """

    def __init__(self, obj, key, grid=None):
        self.grid = grid
        self.obj = obj
        if '!' in key:
            self.key, self.fmt = key.rsplit('!', 1)
        else:
            self.key = key
            self.fmt = None

        if self.key == 'object':
            assert 'osm_id' in obj
            assert 'osm_type' in obj
            self.subobj = OSM_TYPE[obj['osm_type']] + str(obj['osm_id'])
            self.fmt = 'i'
        else:
            done = ''
            self.subobj = self.obj
            for sub in self.key.split('+'):
                done += f"[{sub}]"
                assert sub in self.subobj, \
                    f"Missing attribute {done}. Full object:\n{_pretty(self.obj)}"
                self.subobj = self.subobj[sub]

    def __eq__(self, other):
        if not isinstance(other, str):
            raise NotImplementedError()

        # work around bad quoting by pytest-bdd
        other = other.replace(r'\\', '\\')

        if self.fmt in COMPARISON_FUNCS:
            return COMPARISON_FUNCS[self.fmt](self.subobj, other)

        if self.fmt.startswith(':'):
            return other == f"{{{self.fmt}}}".format(self.subobj)

        if self.fmt == 'wkt':
            return self.compare_wkt(self.subobj, other)

        raise RuntimeError(f"Unknown format string '{self.fmt}'.")

    def __repr__(self):
        k = self.key.replace('+', '][')
        if self.fmt:
            k += '!' + self.fmt
        return f"result[{k}]({self.subobj})"

    def compare_wkt(self, value, expected):
        """ Compare a WKT value against a compact geometry format.
            The function understands the following formats:

              country:<country code>
                 Point geometry guaranteed to be in the given country
              <P>
                 Point geometry
              <P>,...,<P>
                 Line geometry
              (<P>,...,<P>)
                 Polygon geometry

           <P> may either be a coordinate of the form '<x> <y>' or a single
           number. In the latter case it must refer to a point in
           a previously defined grid.
        """
        m = re.fullmatch(r'(POINT)\(([0-9. -]*)\)', value) \
            or re.fullmatch(r'(LINESTRING)\(([0-9,. -]*)\)', value) \
            or re.fullmatch(r'(POLYGON)\(\(([0-9,. -]*)\)\)', value)
        if not m:
            return False

        converted = [list(map(float, pt.split(' ', 1)))
                     for pt in map(str.strip, m[2].split(','))]

        if expected.startswith('country:'):
            ccode = geom[8:].upper()
            assert ccode in ALIASES, f"Geometry error: unknown country {ccode}"
            return m[1] == 'POINT' and \
                   all(math.isclose(p1, p2) for p1, p2 in
                       zip(converted[0], ALIASES[ccode]))

        if ',' not in expected:
            return m[1] == 'POINT' and \
                   all(math.isclose(p1, p2) for p1, p2 in
                       zip(converted[0], self.get_point(expected)))

        if '(' not in expected:
            return m[1] == 'LINESTRING' and \
                   all(math.isclose(p1[0], p2[0]) and math.isclose(p1[1], p2[1]) for p1, p2 in
                       zip(converted, (self.get_point(p) for p in expected.split(','))))

        if m[1] != 'POLYGON':
            return False

        # Polygon comparison is tricky because the polygons don't necessarily
        # end at the same point or have the same winding order.
        # Brute force all possible variants of the expected polygon
        exp_coords = [self.get_point(p) for p in expected[1:-1].split(',')]
        if exp_coords[0] != exp_coords[-1]:
            raise RuntimeError(f"Invalid polygon {expected}. "
                               "First and last point need to be the same")
        for line in (exp_coords[:-1], exp_coords[-1:0:-1]):
            for i in range(len(line)):
                if all(math.isclose(p1[0], p2[0]) and math.isclose(p1[1], p2[1]) for p1, p2 in
                       zip(converted, line[i:] + line[:i])):
                    return True

        return False

    def get_point(self, pt):
        pt = pt.strip()
        if ' ' in pt:
            return list(map(float, pt.split(' ', 1)))

        assert self.grid

        return self.grid.get(pt)


def check_table_content(conn, tablename, data, grid=None, exact=False):
    lines = set(range(1, len(data)))

    cols = []
    for col in data[0]:
        if col == 'object':
            cols.extend(('osm_id', 'osm_type'))
        elif '!' in col:
            name, fmt = col.rsplit('!', 1)
            if fmt == 'wkt':
                cols.append(f"ST_AsText({name}) as {name}")
            else:
                cols.append(name.split('+')[0])
        else:
            cols.append(col.split('+')[0])

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(pysql.SQL(f"SELECT {','.join(cols)} FROM")
                    + pysql.Identifier(tablename))

        table_content = ''
        for row in cur:
            table_content += '\n' + str(row)
            for i in lines:
                for col, value in zip(data[0], data[i]):
                    if ResultAttr(row, col, grid=grid) != value:
                        break
                else:
                    lines.remove(i)
                    break
            else:
                assert not exact, f"Unexpected row in table {tablename}: {row}"

        assert not lines, \
               "Rows not found:\n" \
               + '\n'.join(str(data[i]) for i in lines) \
               + "\nTable content:\n" \
               + table_content


def check_table_has_lines(conn, tablename, osm_type, osm_id, osm_class):
    sql = pysql.SQL("""SELECT count(*) FROM {}
                       WHERE osm_type = %s and osm_id = %s""").format(pysql.Identifier(tablename))
    params = [osm_type, int(osm_id)]
    if osm_class:
        sql += pysql.SQL(' AND class = %s')
        params.append(osm_class)

    with conn.cursor(row_factory=tuple_row) as cur:
        assert cur.execute(sql, params).fetchone()[0] == 0
