# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions to facilitate accessing and comparing the content of DB tables.
"""
import re
import json

from steps.check_functions import Almost

ID_REGEX = re.compile(r"(?P<typ>[NRW])(?P<oid>\d+)(:(?P<cls>\w+))?")

class NominatimID:
    """ Splits a unique identifier for places into its components.
        As place_ids cannot be used for testing, we use a unique
        identifier instead that is of the form <osmtype><osmid>[:<class>].
    """

    def __init__(self, oid):
        self.typ = self.oid = self.cls = None

        if oid is not None:
            m = ID_REGEX.fullmatch(oid)
            assert m is not None, \
                   "ID '{}' not of form <osmtype><osmid>[:<class>]".format(oid)

            self.typ = m.group('typ')
            self.oid = m.group('oid')
            self.cls = m.group('cls')

    def __str__(self):
        if self.cls is None:
            return self.typ + self.oid

        return '{self.typ}{self.oid}:{self.cls}'.format(self=self)

    def query_osm_id(self, cur, query):
        """ Run a query on cursor `cur` using osm ID, type and class. The
            `query` string must contain exactly one placeholder '{}' where
            the 'where' query should go.
        """
        where = 'osm_type = %s and osm_id = %s'
        params = [self.typ, self. oid]

        if self.cls is not None:
            where += ' and class = %s'
            params.append(self.cls)

        cur.execute(query.format(where), params)

    def row_by_place_id(self, cur, table, extra_columns=None):
        """ Get a row by place_id from the given table using cursor `cur`.
            extra_columns may contain a list additional elements for the select
            part of the query.
        """
        pid = self.get_place_id(cur)
        query = "SELECT {} FROM {} WHERE place_id = %s".format(
                    ','.join(['*'] + (extra_columns or [])), table)
        cur.execute(query, (pid, ))

    def get_place_id(self, cur, allow_empty=False):
        """ Look up the place id for the ID. Throws an assertion if the ID
            is not unique.
        """
        self.query_osm_id(cur, "SELECT place_id FROM placex WHERE {}")
        if cur.rowcount == 0 and allow_empty:
            return None

        assert cur.rowcount == 1, \
               "Place ID {!s} not unique. Found {} entries.".format(self, cur.rowcount)

        return cur.fetchone()[0]


class DBRow:
    """ Represents a row from a database and offers comparison functions.
    """
    def __init__(self, nid, db_row, context):
        self.nid = nid
        self.db_row = db_row
        self.context = context

    def assert_row(self, row, exclude_columns):
        """ Check that all columns of the given behave row are contained
            in the database row. Exclude behave rows with the names given
            in the `exclude_columns` list.
        """
        for name, value in zip(row.headings, row.cells):
            if name not in exclude_columns:
                assert self.contains(name, value), self.assert_msg(name, value)

    def contains(self, name, expected):
        """ Check that the DB row contains a column `name` with the given value.
        """
        if '+' in name:
            column, field = name.split('+', 1)
            return self._contains_hstore_value(column, field, expected)

        if name == 'geometry':
            return self._has_geometry(expected)

        if name not in self.db_row:
            return False

        actual = self.db_row[name]

        if expected == '-':
            return actual is None

        if name == 'name' and ':' not in expected:
            return self._compare_column(actual[name], expected)

        if 'place_id' in name:
            return self._compare_place_id(actual, expected)

        if name == 'centroid':
            return self._has_centroid(expected)

        return self._compare_column(actual, expected)

    def _contains_hstore_value(self, column, field, expected):
        if column == 'addr':
            column = 'address'

        if column not in self.db_row:
            return False

        if expected == '-':
            return self.db_row[column] is None or field not in self.db_row[column]

        if self.db_row[column] is None:
            return False

        return self._compare_column(self.db_row[column].get(field), expected)

    def _compare_column(self, actual, expected):
        if isinstance(actual, dict):
            return actual == eval('{' + expected + '}')

        return str(actual) == expected

    def _compare_place_id(self, actual, expected):
       if expected == '0':
            return actual == 0

       with self.context.db.cursor() as cur:
            return NominatimID(expected).get_place_id(cur) == actual

    def _has_centroid(self, expected):
        if expected == 'in geometry':
            with self.context.db.cursor() as cur:
                cur.execute("""SELECT ST_Within(ST_SetSRID(ST_Point({cx}, {cy}), 4326),
                                        ST_SetSRID('{geomtxt}'::geometry, 4326))""".format(**self.db_row))
                return cur.fetchone()[0]

        x, y = expected.split(' ')
        return Almost(float(x)) == self.db_row['cx'] and Almost(float(y)) == self.db_row['cy']

    def _has_geometry(self, expected):
        geom = self.context.osm.parse_geometry(expected, self.context.scene)
        with self.context.db.cursor() as cur:
            cur.execute("""SELECT ST_Equals(ST_SnapToGrid({}, 0.00001, 0.00001),
                                   ST_SnapToGrid(ST_SetSRID('{}'::geometry, 4326), 0.00001, 0.00001))""".format(
                            geom, self.db_row['geomtxt']))
            return cur.fetchone()[0]

    def assert_msg(self, name, value):
        """ Return a string with an informative message for a failed compare.
        """
        msg = "\nBad column '{}' in row '{!s}'.".format(name, self.nid)
        actual = self._get_actual(name)
        if actual is not None:
            msg += " Expected: {}, got: {}.".format(value, actual)
        else:
            msg += " No such column."

        return msg + "\nFull DB row: {}".format(json.dumps(dict(self.db_row), indent=4, default=str))

    def _get_actual(self, name):
        if '+' in name:
            column, field = name.split('+', 1)
            if column == 'addr':
                column = 'address'
            return (self.db_row.get(column) or {}).get(field)

        if name == 'geometry':
            return self.db_row['geomtxt']

        if name not in self.db_row:
            return None

        if name == 'centroid':
            return "POINT({cx} {cy})".format(**self.db_row)

        actual = self.db_row[name]

        if 'place_id' in name:
            if actual is None:
                return '<null>'

            if actual == 0:
                return "place ID 0"

            with self.context.db.cursor() as cur:
                cur.execute("""SELECT osm_type, osm_id, class
                               FROM placex WHERE place_id = %s""",
                            (actual, ))

                if cur.rowcount == 1:
                    return "{0[0]}{0[1]}:{0[2]}".format(cur.fetchone())

                return "[place ID {} not found]".format(actual)

        return actual
