"""
Tests for property table manpulation.
"""
import pytest

from nominatim.db import properties

@pytest.fixture
def prop_table(table_factory):
    table_factory('nominatim_properties', 'property TEXT, value TEXT')


def test_get_property_existing(prop_table, temp_db_conn, temp_db_cursor):
    temp_db_cursor.execute("INSERT INTO nominatim_properties VALUES('foo', 'bar')")

    assert properties.get_property(temp_db_conn, 'foo') == 'bar'


def test_get_property_unknown(prop_table, temp_db_conn, temp_db_cursor):
    temp_db_cursor.execute("INSERT INTO nominatim_properties VALUES('other', 'bar')")

    assert properties.get_property(temp_db_conn, 'foo') is None


@pytest.mark.parametrize("prefill", (True, False))
def test_set_property_new(prop_table, temp_db_conn, temp_db_cursor, prefill):
    if prefill:
        temp_db_cursor.execute("INSERT INTO nominatim_properties VALUES('something', 'bar')")

    properties.set_property(temp_db_conn, 'something', 'else')

    assert temp_db_cursor.scalar("""SELECT value FROM nominatim_properties
                                    WHERE property = 'something'""") == 'else'

    assert properties.get_property(temp_db_conn, 'something') == 'else'
