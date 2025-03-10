# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for status table manipulation.
"""
import datetime as dt

import pytest

import nominatim_db.db.status
from nominatim_db.errors import UsageError

OSM_NODE_DATA = """\
<osm version="0.6" generator="OpenStreetMap server" copyright="OpenStreetMap and contributors" attribution="http://www.openstreetmap.org/copyright" license="http://opendatacommons.org/licenses/odbl/1-0/">
<node id="45673" visible="true" version="1" changeset="2047" timestamp="2006-01-27T22:09:10Z" user="Foo" uid="111" lat="48.7586670" lon="8.1343060">
</node>
</osm>
"""  # noqa


def iso_date(date):
    return dt.datetime.strptime(date, nominatim_db.db.status.ISODATE_FORMAT)\
               .replace(tzinfo=dt.timezone.utc)


@pytest.fixture(autouse=True)
def setup_status_table(status_table):
    pass


@pytest.mark.parametrize('offline', [True, False])
def test_compute_database_date_from_osm2pgsql(table_factory, temp_db_conn, offline):
    table_factory('osm2pgsql_properties', 'property TEXT, value TEXT',
                  content=(('current_timestamp', '2024-01-03T23:45:54Z'), ))

    date = nominatim_db.db.status.compute_database_date(temp_db_conn, offline=offline)
    assert date == iso_date('2024-01-03T23:45:54')


def test_compute_database_date_from_osm2pgsql_nodata(table_factory, temp_db_conn):
    table_factory('osm2pgsql_properties', 'property TEXT, value TEXT')

    with pytest.raises(UsageError,
                       match='Cannot determine database date from data in offline mode'):
        nominatim_db.db.status.compute_database_date(temp_db_conn, offline=True)


def test_compute_database_date_place_empty(place_table, temp_db_conn):
    with pytest.raises(UsageError):
        nominatim_db.db.status.compute_database_date(temp_db_conn)


def test_compute_database_date_valid(monkeypatch, place_row, temp_db_conn):
    place_row(osm_type='N', osm_id=45673)

    requested_url = []

    def mock_url(url):
        requested_url.append(url)
        return OSM_NODE_DATA

    monkeypatch.setattr(nominatim_db.db.status, "get_url", mock_url)

    date = nominatim_db.db.status.compute_database_date(temp_db_conn)

    assert requested_url == ['https://www.openstreetmap.org/api/0.6/node/45673/1']
    assert date == iso_date('2006-01-27T22:09:10')


def test_compute_database_broken_api(monkeypatch, place_row, temp_db_conn):
    place_row(osm_type='N', osm_id=45673)

    requested_url = []

    def mock_url(url):
        requested_url.append(url)
        return '<osm version="0.6" generator="OpenStre'

    monkeypatch.setattr(nominatim_db.db.status, "get_url", mock_url)

    with pytest.raises(UsageError):
        nominatim_db.db.status.compute_database_date(temp_db_conn)


def test_set_status_empty_table(temp_db_conn, temp_db_cursor):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim_db.db.status.set_status(temp_db_conn, date=date)

    assert temp_db_cursor.row_set("SELECT * FROM import_status") == {(date, None, True)}


def test_set_status_filled_table(temp_db_conn, temp_db_cursor):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim_db.db.status.set_status(temp_db_conn, date=date)

    assert temp_db_cursor.table_rows('import_status') == 1

    date = dt.datetime.fromordinal(1000100).replace(tzinfo=dt.timezone.utc)
    nominatim_db.db.status.set_status(temp_db_conn, date=date, seq=456, indexed=False)

    assert temp_db_cursor.row_set("SELECT * FROM import_status") == {(date, 456, False)}


def test_set_status_missing_date(temp_db_conn, temp_db_cursor):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim_db.db.status.set_status(temp_db_conn, date=date)

    assert temp_db_cursor.table_rows('import_status') == 1

    nominatim_db.db.status.set_status(temp_db_conn, date=None, seq=456, indexed=False)

    assert temp_db_cursor.row_set("SELECT * FROM import_status") == {(date, 456, False)}


def test_get_status_empty_table(temp_db_conn):
    assert nominatim_db.db.status.get_status(temp_db_conn) == (None, None, None)


def test_get_status_success(temp_db_conn):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim_db.db.status.set_status(temp_db_conn, date=date, seq=667, indexed=False)

    assert nominatim_db.db.status.get_status(temp_db_conn) == (date, 667, False)


@pytest.mark.parametrize("old_state", [True, False])
@pytest.mark.parametrize("new_state", [True, False])
def test_set_indexed(temp_db_conn, temp_db_cursor, old_state, new_state):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim_db.db.status.set_status(temp_db_conn, date=date, indexed=old_state)
    nominatim_db.db.status.set_indexed(temp_db_conn, new_state)

    assert temp_db_cursor.scalar("SELECT indexed FROM import_status") == new_state


def test_set_indexed_empty_status(temp_db_conn, temp_db_cursor):
    nominatim_db.db.status.set_indexed(temp_db_conn, True)

    assert temp_db_cursor.table_rows("import_status") == 0


def test_log_status(temp_db_conn, temp_db_cursor):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    start = dt.datetime.now() - dt.timedelta(hours=1)

    nominatim_db.db.status.set_status(temp_db_conn, date=date, seq=56)
    nominatim_db.db.status.log_status(temp_db_conn, start, 'index')

    temp_db_conn.commit()

    assert temp_db_cursor.table_rows("import_osmosis_log") == 1
    assert temp_db_cursor.scalar("SELECT batchseq FROM import_osmosis_log") == 56
    assert temp_db_cursor.scalar("SELECT event FROM import_osmosis_log") == 'index'
