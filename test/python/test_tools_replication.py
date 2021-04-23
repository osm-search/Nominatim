"""
Tests for replication functionality.
"""
import datetime as dt
import time

import pytest
from osmium.replication.server import OsmosisState

import nominatim.tools.replication
import nominatim.db.status as status
from nominatim.errors import UsageError

OSM_NODE_DATA = """\
<osm version="0.6" generator="OpenStreetMap server" copyright="OpenStreetMap and contributors" attribution="http://www.openstreetmap.org/copyright" license="http://opendatacommons.org/licenses/odbl/1-0/">
<node id="100" visible="true" version="1" changeset="2047" timestamp="2006-01-27T22:09:10Z" user="Foo" uid="111" lat="48.7586670" lon="8.1343060">
</node>
</osm>
"""

### init replication

def test_init_replication_bad_base_url(monkeypatch, status_table, place_row, temp_db_conn, temp_db_cursor):
    place_row(osm_type='N', osm_id=100)

    monkeypatch.setattr(nominatim.db.status, "get_url", lambda u : OSM_NODE_DATA)

    with pytest.raises(UsageError, match="Failed to reach replication service"):
        nominatim.tools.replication.init_replication(temp_db_conn, 'https://test.io')


def test_init_replication_success(monkeypatch, status_table, place_row, temp_db_conn, temp_db_cursor):
    place_row(osm_type='N', osm_id=100)

    monkeypatch.setattr(nominatim.db.status, "get_url", lambda u : OSM_NODE_DATA)
    monkeypatch.setattr(nominatim.tools.replication.ReplicationServer,
                        "timestamp_to_sequence",
                        lambda self, date: 234)

    nominatim.tools.replication.init_replication(temp_db_conn, 'https://test.io')

    temp_db_cursor.execute("SELECT * FROM import_status")

    expected_date = dt.datetime.strptime('2006-01-27T19:09:10', status.ISODATE_FORMAT)\
                        .replace(tzinfo=dt.timezone.utc)
    assert temp_db_cursor.rowcount == 1
    assert temp_db_cursor.fetchone() == [expected_date, 234, True]


### checking for updates

def test_check_for_updates_empty_status_table(status_table, temp_db_conn):
    assert nominatim.tools.replication.check_for_updates(temp_db_conn, 'https://test.io') == 254


def test_check_for_updates_seq_not_set(status_table, temp_db_conn):
    status.set_status(temp_db_conn, dt.datetime.now(dt.timezone.utc))

    assert nominatim.tools.replication.check_for_updates(temp_db_conn, 'https://test.io') == 254


def test_check_for_updates_no_state(monkeypatch, status_table, temp_db_conn):
    status.set_status(temp_db_conn, dt.datetime.now(dt.timezone.utc), seq=345)

    monkeypatch.setattr(nominatim.tools.replication.ReplicationServer,
                        "get_state_info", lambda self: None)

    assert nominatim.tools.replication.check_for_updates(temp_db_conn, 'https://test.io') == 253


@pytest.mark.parametrize("server_sequence,result", [(344, 2), (345, 2), (346, 0)])
def test_check_for_updates_no_new_data(monkeypatch, status_table, temp_db_conn,
                                       server_sequence, result):
    date = dt.datetime.now(dt.timezone.utc)
    status.set_status(temp_db_conn, date, seq=345)

    monkeypatch.setattr(nominatim.tools.replication.ReplicationServer,
                        "get_state_info",
                        lambda self: OsmosisState(server_sequence, date))

    assert nominatim.tools.replication.check_for_updates(temp_db_conn, 'https://test.io') == result


### updating

@pytest.fixture
def update_options(tmpdir):
    return dict(base_url='https://test.io',
                   indexed_only=False,
                   update_interval=3600,
                   import_file=tmpdir / 'foo.osm',
                   max_diff_size=1)

def test_update_empty_status_table(status_table, temp_db_conn):
    with pytest.raises(UsageError):
        nominatim.tools.replication.update(temp_db_conn, {})


def test_update_already_indexed(status_table, temp_db_conn):
    status.set_status(temp_db_conn, dt.datetime.now(dt.timezone.utc), seq=34, indexed=False)

    assert nominatim.tools.replication.update(temp_db_conn, dict(indexed_only=True)) \
             == nominatim.tools.replication.UpdateState.MORE_PENDING


def test_update_no_data_no_sleep(monkeypatch, status_table, temp_db_conn, update_options):
    date = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=1)
    status.set_status(temp_db_conn, date, seq=34)

    monkeypatch.setattr(nominatim.tools.replication.ReplicationServer,
                        "apply_diffs",
                        lambda *args, **kwargs: None)

    sleeptime = []
    monkeypatch.setattr(time, 'sleep', lambda s: sleeptime.append(s))

    assert nominatim.tools.replication.update(temp_db_conn, update_options) \
             == nominatim.tools.replication.UpdateState.NO_CHANGES

    assert not sleeptime


def test_update_no_data_sleep(monkeypatch, status_table, temp_db_conn, update_options):
    date = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=30)
    status.set_status(temp_db_conn, date, seq=34)

    monkeypatch.setattr(nominatim.tools.replication.ReplicationServer,
                        "apply_diffs",
                        lambda *args, **kwargs: None)

    sleeptime = []
    monkeypatch.setattr(time, 'sleep', lambda s: sleeptime.append(s))

    assert nominatim.tools.replication.update(temp_db_conn, update_options) \
             == nominatim.tools.replication.UpdateState.NO_CHANGES

    assert len(sleeptime) == 1
    assert sleeptime[0] < 3600
    assert sleeptime[0] > 0
