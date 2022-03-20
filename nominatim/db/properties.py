# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Query and access functions for the in-database property table.
"""

def set_property(conn, name, value):
    """ Add or replace the propery with the given name.
    """
    with conn.cursor() as cur:
        cur.execute('SELECT value FROM nominatim_properties WHERE property = %s',
                    (name, ))

        if cur.rowcount == 0:
            sql = 'INSERT INTO nominatim_properties (value, property) VALUES (%s, %s)'
        else:
            sql = 'UPDATE nominatim_properties SET value = %s WHERE property = %s'

        cur.execute(sql, (value, name))
    conn.commit()

def get_property(conn, name):
    """ Return the current value of the given propery or None if the property
        is not set.
    """
    if not conn.table_exists('nominatim_properties'):
        return None

    with conn.cursor() as cur:
        cur.execute('SELECT value FROM nominatim_properties WHERE property = %s',
                    (name, ))

        return cur.fetchone()[0] if cur.rowcount > 0 else None
