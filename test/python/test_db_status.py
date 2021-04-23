"""
Tests for status table manipulation.
"""
import datetime as dt

import pytest

import nominatim.db.status
from nominatim.errors import UsageError

def test_compute_database_date_place_empty(status_table, place_table, temp_db_conn):
    with pytest.raises(UsageError):
        nominatim.db.status.compute_database_date(temp_db_conn)

OSM_NODE_DATA = """\
<osm version="0.6" generator="OpenStreetMap server" copyright="OpenStreetMap and contributors" attribution="http://www.openstreetmap.org/copyright" license="http://opendatacommons.org/licenses/odbl/1-0/">
<node id="45673" visible="true" version="1" changeset="2047" timestamp="2006-01-27T22:09:10Z" user="Foo" uid="111" lat="48.7586670" lon="8.1343060">
</node>
</osm>
"""

def iso_date(date):
    return dt.datetime.strptime(date, nominatim.db.status.ISODATE_FORMAT)\
               .replace(tzinfo=dt.timezone.utc)


def test_compute_database_date_valid(monkeypatch, status_table, place_row, temp_db_conn):
    place_row(osm_type='N', osm_id=45673)

    requested_url = []
    def mock_url(url):
        requested_url.append(url)
        return OSM_NODE_DATA

    monkeypatch.setattr(nominatim.db.status, "get_url", mock_url)

    date = nominatim.db.status.compute_database_date(temp_db_conn)

    assert requested_url == ['https://www.openstreetmap.org/api/0.6/node/45673/1']
    assert date == iso_date('2006-01-27T22:09:10')


def test_compute_database_broken_api(monkeypatch, status_table, place_row, temp_db_conn):
    place_row(osm_type='N', osm_id=45673)

    requested_url = []
    def mock_url(url):
        requested_url.append(url)
        return '<osm version="0.6" generator="OpenStre'

    monkeypatch.setattr(nominatim.db.status, "get_url", mock_url)

    with pytest.raises(UsageError):
        date = nominatim.db.status.compute_database_date(temp_db_conn)


def test_set_status_empty_table(status_table, temp_db_conn, temp_db_cursor):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim.db.status.set_status(temp_db_conn, date=date)

    temp_db_cursor.execute("SELECT * FROM import_status")

    assert temp_db_cursor.rowcount == 1
    assert temp_db_cursor.fetchone() == [date, None, True]


def test_set_status_filled_table(status_table, temp_db_conn, temp_db_cursor):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim.db.status.set_status(temp_db_conn, date=date)

    assert 1 == temp_db_cursor.scalar("SELECT count(*) FROM import_status")

    date = dt.datetime.fromordinal(1000100).replace(tzinfo=dt.timezone.utc)
    nominatim.db.status.set_status(temp_db_conn, date=date, seq=456, indexed=False)

    temp_db_cursor.execute("SELECT * FROM import_status")

    assert temp_db_cursor.rowcount == 1
    assert temp_db_cursor.fetchone() == [date, 456, False]


def test_set_status_missing_date(status_table, temp_db_conn, temp_db_cursor):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim.db.status.set_status(temp_db_conn, date=date)

    assert 1 == temp_db_cursor.scalar("SELECT count(*) FROM import_status")

    nominatim.db.status.set_status(temp_db_conn, date=None, seq=456, indexed=False)

    temp_db_cursor.execute("SELECT * FROM import_status")

    assert temp_db_cursor.rowcount == 1
    assert temp_db_cursor.fetchone() == [date, 456, False]


def test_get_status_empty_table(status_table, temp_db_conn):
    assert nominatim.db.status.get_status(temp_db_conn) == (None, None, None)


def test_get_status_success(status_table, temp_db_conn):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim.db.status.set_status(temp_db_conn, date=date, seq=667, indexed=False)

    assert nominatim.db.status.get_status(temp_db_conn) == \
             (date, 667, False)


@pytest.mark.parametrize("old_state", [True, False])
@pytest.mark.parametrize("new_state", [True, False])
def test_set_indexed(status_table, temp_db_conn, temp_db_cursor, old_state, new_state):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    nominatim.db.status.set_status(temp_db_conn, date=date, indexed=old_state)
    nominatim.db.status.set_indexed(temp_db_conn, new_state)

    assert temp_db_cursor.scalar("SELECT indexed FROM import_status") == new_state


def test_set_indexed_empty_status(status_table, temp_db_conn, temp_db_cursor):
    nominatim.db.status.set_indexed(temp_db_conn, True)

    assert temp_db_cursor.scalar("SELECT count(*) FROM import_status") == 0


def text_log_status(status_table, temp_db_conn):
    date = dt.datetime.fromordinal(1000000).replace(tzinfo=dt.timezone.utc)
    start = dt.datetime.now() - dt.timedelta(hours=1)
    nominatim.db.status.set_status(temp_db_conn, date=date, seq=56)
    nominatim.db.status.log_status(temp_db_conn, start, 'index')

    assert temp_db_cursor.scalar("SELECT count(*) FROM import_osmosis_log") == 1
    assert temp_db_cursor.scalar("SELECT seq FROM import_osmosis_log") == 56
    assert temp_db_cursor.scalar("SELECT date FROM import_osmosis_log") == date
