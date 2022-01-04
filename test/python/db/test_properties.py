# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for property table manpulation.
"""
import pytest

from nominatim.db import properties

@pytest.fixture
def property_factory(property_table, temp_db_cursor):
    """ A function fixture that adds a property into the property table.
    """
    def _add_property(name, value):
        temp_db_cursor.execute("INSERT INTO nominatim_properties VALUES(%s, %s)",
                               (name, value))

    return _add_property


def test_get_property_existing(property_factory, temp_db_conn):
    property_factory('foo', 'bar')

    assert properties.get_property(temp_db_conn, 'foo') == 'bar'


def test_get_property_unknown(property_factory, temp_db_conn):
    property_factory('other', 'bar')

    assert properties.get_property(temp_db_conn, 'foo') is None


@pytest.mark.parametrize("prefill", (True, False))
def test_set_property_new(property_factory, temp_db_conn, temp_db_cursor, prefill):
    if prefill:
        property_factory('something', 'bar')

    properties.set_property(temp_db_conn, 'something', 'else')

    assert temp_db_cursor.scalar("""SELECT value FROM nominatim_properties
                                    WHERE property = 'something'""") == 'else'

    assert properties.get_property(temp_db_conn, 'something') == 'else'
