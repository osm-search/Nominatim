"""
Functions for updating a database from a replication source.
"""
import datetime as dt
from enum import Enum
import logging
import time

from osmium.replication.server import ReplicationServer
from osmium import WriteHandler

from ..db import status
from .exec_utils import run_osm2pgsql
from ..errors import UsageError

LOG = logging.getLogger()

def init_replication(conn, base_url):
    """ Set up replication for the server at the given base URL.
    """
    LOG.info("Using replication source: %s", base_url)
    date = status.compute_database_date(conn)

    # margin of error to make sure we get all data
    date -= dt.timedelta(hours=3)

    repl = ReplicationServer(base_url)

    seq = repl.timestamp_to_sequence(date)

    if seq is None:
        LOG.fatal("Cannot reach the configured replication service '%s'.\n"
                  "Does the URL point to a directory containing OSM update data?",
                  base_url)
        raise UsageError("Failed to reach replication service")

    status.set_status(conn, date=date, seq=seq)

    LOG.warning("Updates intialised at sequence %s (%s)", seq, date)


def check_for_updates(conn, base_url):
    """ Check if new data is available from the replication service at the
        given base URL.
    """
    _, seq, _ = status.get_status(conn)

    if seq is None:
        LOG.error("Replication not set up. "
                  "Please run 'nominatim replication --init' first.")
        return 254

    state = ReplicationServer(base_url).get_state_info()

    if state is None:
        LOG.error("Cannot get state for URL %s.", base_url)
        return 253

    if state.sequence <= seq:
        LOG.warning("Database is up to date.")
        return 2

    LOG.warning("New data available (%i => %i).", seq, state.sequence)
    return 0

class UpdateState(Enum):
    """ Possible states after an update has run.
    """

    UP_TO_DATE = 0
    MORE_PENDING = 2
    NO_CHANGES = 3


def update(conn, options):
    """ Update database from the next batch of data. Returns the state of
        updates according to `UpdateState`.
    """
    startdate, startseq, indexed = status.get_status(conn)

    if startseq is None:
        LOG.error("Replication not set up. "
                  "Please run 'nominatim replication --init' first.")
        raise UsageError("Replication not set up.")

    if not indexed and options['indexed_only']:
        LOG.info("Skipping update. There is data that needs indexing.")
        return UpdateState.MORE_PENDING

    last_since_update = dt.datetime.now(dt.timezone.utc) - startdate
    update_interval = dt.timedelta(seconds=options['update_interval'])
    if last_since_update < update_interval:
        duration = (update_interval - last_since_update).seconds
        LOG.warning("Sleeping for %s sec before next update.", duration)
        time.sleep(duration)

    if options['import_file'].exists():
        options['import_file'].unlink()

    # Read updates into file.
    repl = ReplicationServer(options['base_url'])

    outhandler = WriteHandler(str(options['import_file']))
    endseq = repl.apply_diffs(outhandler, startseq + 1,
                              max_size=options['max_diff_size'] * 1024)
    outhandler.close()

    if endseq is None:
        return UpdateState.NO_CHANGES

    # Consume updates with osm2pgsql.
    options['append'] = True
    run_osm2pgsql(options)

    # Write the current status to the file
    endstate = repl.get_state_info(endseq)
    status.set_status(conn, endstate.timestamp, seq=endseq, indexed=False)

    return UpdateState.UP_TO_DATE
