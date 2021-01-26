"""
Functions for updating a database from a replication source.
"""
import datetime
import logging

from osmium.replication.server import ReplicationServer

from ..db import status

LOG = logging.getLogger()

def init_replication(conn, base_url):
    """ Set up replication for the server at the given base URL.
    """
    LOG.info("Using replication source: %s", base_url)
    date = status.compute_database_date(conn)

    # margin of error to make sure we get all data
    date -= datetime.timedelta(hours=3)

    repl = ReplicationServer(base_url)

    seq = repl.timestamp_to_sequence(date)

    if seq is None:
        LOG.fatal("Cannot reach the configured replication service '%s'.\n"
                  "Does the URL point to a directory containing OSM update data?",
                  base_url)
        raise RuntimeError("Failed to reach replication service")

    status.set_status(conn, date=date, seq=seq)

    LOG.warning("Updates intialised at sequence %s (%s)", seq, date)
