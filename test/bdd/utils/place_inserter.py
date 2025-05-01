# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Helper classes for filling the place table.
"""
import random
import string

from .geometry_alias import ALIASES


class PlaceColumn:
    """ Helper class to collect contents from a BDD table row and
        insert it into the place table.
    """
    def __init__(self, grid=None):
        self.columns = {'admin_level': 15}
        self.grid = grid
        self.geometry = None

    def add_row(self, headings, row, force_name):
        """ Parse the content from the given behave row as place column data.
        """
        for name, value in zip(headings, row):
            self._add(name, value)

        assert 'osm_type' in self.columns, "osm column missing"

        if force_name and 'name' not in self.columns:
            self._add_hstore(
                'name',
                'name',
                ''.join(random.choices(string.printable, k=random.randrange(30))),
            )

        return self

    def _add(self, key, value):
        if hasattr(self, '_set_key_' + key):
            getattr(self, '_set_key_' + key)(value)
        elif key.startswith('name+'):
            self._add_hstore('name', key[5:], value)
        elif key.startswith('extra+'):
            self._add_hstore('extratags', key[6:], value)
        elif key.startswith('addr+'):
            self._add_hstore('address', key[5:], value)
        elif key in ('name', 'address', 'extratags'):
            self.columns[key] = eval('{' + value + '}')
        else:
            assert key in ('class', 'type'), "Unknown column '{}'.".format(key)
            self.columns[key] = None if value == '' else value

    def _set_key_name(self, value):
        self._add_hstore('name', 'name', value)

    def _set_key_osm(self, value):
        assert value[0] in 'NRW' and value[1:].isdigit(), \
               "OSM id needs to be of format <NRW><id>."

        self.columns['osm_type'] = value[0]
        self.columns['osm_id'] = int(value[1:])

    def _set_key_admin(self, value):
        self.columns['admin_level'] = int(value)

    def _set_key_housenr(self, value):
        if value:
            self._add_hstore('address', 'housenumber', value)

    def _set_key_postcode(self, value):
        if value:
            self._add_hstore('address', 'postcode', value)

    def _set_key_street(self, value):
        if value:
            self._add_hstore('address', 'street', value)

    def _set_key_addr_place(self, value):
        if value:
            self._add_hstore('address', 'place', value)

    def _set_key_country(self, value):
        if value:
            self._add_hstore('address', 'country', value)

    def _set_key_geometry(self, value):
        if value.startswith('country:'):
            ccode = value[8:].upper()
            self.geometry = "ST_SetSRID(ST_Point({}, {}), 4326)".format(*ALIASES[ccode])
        elif ',' not in value:
            if self.grid:
                pt = self.grid.parse_point(value)
            else:
                pt = value.split(' ')
            self.geometry = f"ST_SetSRID(ST_Point({pt[0]}, {pt[1]}), 4326)"
        elif '(' not in value:
            if self.grid:
                coords = ','.join(' '.join(f"{p:.7f}" for p in pt)
                                  for pt in self.grid.parse_line(value))
            else:
                coords = value
            self.geometry = f"'srid=4326;LINESTRING({coords})'::geometry"
        else:
            if self.grid:
                coords = ','.join(' '.join(f"{p:.7f}" for p in pt)
                                  for pt in self.grid.parse_line(value[1:-1]))
            else:
                coords = value[1:-1]
            self.geometry = f"'srid=4326;POLYGON(({coords}))'::geometry"

    def _add_hstore(self, column, key, value):
        if column in self.columns:
            self.columns[column][key] = value
        else:
            self.columns[column] = {key: value}

    def db_delete(self, cursor):
        """ Issue a delete for the given OSM object.
        """
        cursor.execute('DELETE FROM place WHERE osm_type = %s and osm_id = %s',
                       (self.columns['osm_type'], self.columns['osm_id']))

    def db_insert(self, cursor):
        """ Insert the collected data into the database.
        """
        if self.columns['osm_type'] == 'N' and self.geometry is None:
            pt = self.grid.get(str(self.columns['osm_id'])) if self.grid else None
            if pt is None:
                pt = (random.uniform(-180, 180), random.uniform(-90, 90))

            self.geometry = "ST_SetSRID(ST_Point({}, {}), 4326)".format(*pt)
        else:
            assert self.geometry is not None, "Geometry missing"

        query = 'INSERT INTO place ({}, geometry) values({}, {})'.format(
            ','.join(self.columns.keys()),
            ','.join(['%s' for x in range(len(self.columns))]),
            self.geometry)
        cursor.execute(query, list(self.columns.values()))
