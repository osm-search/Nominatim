"""
Tests for replication functionality.
"""
import datetime as dt

import pytest

import nominatim.tools.replication

OSM_NODE_DATA = """\
<osm version="0.6" generator="OpenStreetMap server" copyright="OpenStreetMap and contributors" attribution="http://www.openstreetmap.org/copyright" license="http://opendatacommons.org/licenses/odbl/1-0/">
<node id="100" visible="true" version="1" changeset="2047" timestamp="2006-01-27T22:09:10Z" user="Foo" uid="111" lat="48.7586670" lon="8.1343060">
</node>
</osm>
"""


def test_init_replication_bad_base_url(monkeypatch, status_table, place_row, temp_db_conn, temp_db_cursor):
    place_row(osm_type='N', osm_id=100)

    monkeypatch.setattr(nominatim.db.status, "get_url", lambda u : OSM_NODE_DATA)

    with pytest.raises(RuntimeError, match="Failed to reach replication service"):
        nominatim.tools.replication.init_replication(temp_db_conn, 'https://test.io')


def test_init_replication_success(monkeypatch, status_table, place_row, temp_db_conn, temp_db_cursor):
    place_row(osm_type='N', osm_id=100)

    monkeypatch.setattr(nominatim.db.status, "get_url", lambda u : OSM_NODE_DATA)
    monkeypatch.setattr(nominatim.tools.replication.ReplicationServer,
                        "timestamp_to_sequence",
                        lambda self, date: 234)

    nominatim.tools.replication.init_replication(temp_db_conn, 'https://test.io')

    temp_db_cursor.execute("SELECT * FROM import_status")

    expected_date = dt.datetime.fromisoformat('2006-01-27T19:09:10').replace(tzinfo=dt.timezone.utc)
    assert temp_db_cursor.rowcount == 1
    assert temp_db_cursor.fetchone() == [expected_date, 234, True]
