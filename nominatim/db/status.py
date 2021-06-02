"""
Access and helper functions for the status and status log table.
"""
import datetime as dt
import logging
import re

from nominatim.tools.exec_utils import get_url
from nominatim.errors import UsageError

LOG = logging.getLogger()
ISODATE_FORMAT = '%Y-%m-%dT%H:%M:%S'

def compute_database_date(conn):
    """ Determine the date of the database from the newest object in the
        data base.
    """
    # First, find the node with the highest ID in the database
    with conn.cursor() as cur:
        if conn.table_exists('place'):
            osmid = cur.scalar("SELECT max(osm_id) FROM place WHERE osm_type='N'")
        else:
            osmid = cur.scalar("SELECT max(osm_id) FROM placex WHERE osm_type='N'")

        if osmid is None:
            LOG.fatal("No data found in the database.")
            raise UsageError("No data found in the database.")

    LOG.info("Using node id %d for timestamp lookup", osmid)
    # Get the node from the API to find the timestamp when it was created.
    node_url = 'https://www.openstreetmap.org/api/0.6/node/{}/1'.format(osmid)
    data = get_url(node_url)

    match = re.search(r'timestamp="((\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}))Z"', data)

    if match is None:
        LOG.fatal("The node data downloaded from the API does not contain valid data.\n"
                  "URL used: %s", node_url)
        raise UsageError("Bad API data.")

    LOG.debug("Found timestamp %s", match.group(1))

    return dt.datetime.strptime(match.group(1), ISODATE_FORMAT).replace(tzinfo=dt.timezone.utc)


def set_status(conn, date, seq=None, indexed=True):
    """ Replace the current status with the given status. If date is `None`
        then only sequence and indexed will be updated as given. Otherwise
        the whole status is replaced.
    """
    assert date is None or date.tzinfo == dt.timezone.utc
    with conn.cursor() as cur:
        if date is None:
            cur.execute("UPDATE import_status set sequence_id = %s, indexed = %s",
                        (seq, indexed))
        else:
            cur.execute("TRUNCATE TABLE import_status")
            cur.execute("""INSERT INTO import_status (lastimportdate, sequence_id, indexed)
                           VALUES (%s, %s, %s)""", (date, seq, indexed))

    conn.commit()


def get_status(conn):
    """ Return the current status as a triple of (date, sequence, indexed).
        If status has not been set up yet, a triple of None is returned.
    """
    with conn.cursor() as cur:
        cur.execute("SELECT * FROM import_status LIMIT 1")
        if cur.rowcount < 1:
            return None, None, None

        row = cur.fetchone()
        return row['lastimportdate'], row['sequence_id'], row['indexed']


def set_indexed(conn, state):
    """ Set the indexed flag in the status table to the given state.
    """
    with conn.cursor() as cur:
        cur.execute("UPDATE import_status SET indexed = %s", (state, ))
    conn.commit()


def log_status(conn, start, event, batchsize=None):
    """ Write a new status line to the `import_osmosis_log` table.
    """
    with conn.cursor() as cur:
        cur.execute("""INSERT INTO import_osmosis_log
                       (batchend, batchseq, batchsize, starttime, endtime, event)
                       SELECT lastimportdate, sequence_id, %s, %s, now(), %s FROM import_status""",
                    (batchsize, start, event))
