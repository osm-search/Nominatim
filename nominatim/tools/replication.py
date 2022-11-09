# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for updating a database from a replication source.
"""
from typing import ContextManager, MutableMapping, Any, Generator, cast, Iterator
from contextlib import contextmanager
import datetime as dt
from enum import Enum
import logging
import time
import types
import urllib.request as urlrequest

import requests
from nominatim.db import status
from nominatim.db.connection import Connection
from nominatim.tools.exec_utils import run_osm2pgsql
from nominatim.errors import UsageError

try:
    from osmium.replication.server import ReplicationServer
    from osmium import WriteHandler
    from osmium import version as pyo_version
except ImportError as exc:
    logging.getLogger().critical("pyosmium not installed. Replication functions not available.\n"
                                 "To install pyosmium via pip: pip3 install osmium")
    raise UsageError("replication tools not available") from exc

LOG = logging.getLogger()

def init_replication(conn: Connection, base_url: str,
                     socket_timeout: int = 60) -> None:
    """ Set up replication for the server at the given base URL.
    """
    LOG.info("Using replication source: %s", base_url)
    date = status.compute_database_date(conn)

    # margin of error to make sure we get all data
    date -= dt.timedelta(hours=3)

    with _make_replication_server(base_url, socket_timeout) as repl:
        seq = repl.timestamp_to_sequence(date)

    if seq is None:
        LOG.fatal("Cannot reach the configured replication service '%s'.\n"
                  "Does the URL point to a directory containing OSM update data?",
                  base_url)
        raise UsageError("Failed to reach replication service")

    status.set_status(conn, date=date, seq=seq)

    LOG.warning("Updates initialised at sequence %s (%s)", seq, date)


def check_for_updates(conn: Connection, base_url: str,
                      socket_timeout: int = 60) -> int:
    """ Check if new data is available from the replication service at the
        given base URL.
    """
    _, seq, _ = status.get_status(conn)

    if seq is None:
        LOG.error("Replication not set up. "
                  "Please run 'nominatim replication --init' first.")
        return 254

    with _make_replication_server(base_url, socket_timeout) as repl:
        state = repl.get_state_info()

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


def update(conn: Connection, options: MutableMapping[str, Any],
           socket_timeout: int = 60) -> UpdateState:
    """ Update database from the next batch of data. Returns the state of
        updates according to `UpdateState`.
    """
    startdate, startseq, indexed = status.get_status(conn)

    if startseq is None:
        LOG.error("Replication not set up. "
                  "Please run 'nominatim replication --init' first.")
        raise UsageError("Replication not set up.")

    assert startdate is not None

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
    with _make_replication_server(options['base_url'], socket_timeout) as repl:
        outhandler = WriteHandler(str(options['import_file']))
        endseq = repl.apply_diffs(outhandler, startseq + 1,
                                  max_size=options['max_diff_size'] * 1024)
        outhandler.close()

        if endseq is None:
            return UpdateState.NO_CHANGES

        # Consume updates with osm2pgsql.
        options['append'] = True
        options['disable_jit'] = conn.server_version_tuple() >= (11, 0)
        run_osm2pgsql(options)

        # Write the current status to the file
        endstate = repl.get_state_info(endseq)
        status.set_status(conn, endstate.timestamp if endstate else None,
                          seq=endseq, indexed=False)

    return UpdateState.UP_TO_DATE


def _make_replication_server(url: str, timeout: int) -> ContextManager[ReplicationServer]:
    """ Returns a ReplicationServer in form of a context manager.

        Creates a light wrapper around older versions of pyosmium that did
        not support the context manager interface.
    """
    if hasattr(ReplicationServer, '__enter__'):
        # Patches the open_url function for pyosmium >= 3.2
        # where the socket timeout is no longer respected.
        def patched_open_url(self: ReplicationServer, url: urlrequest.Request) -> Any:
            """ Download a resource from the given URL and return a byte sequence
                of the content.
            """
            headers = {"User-Agent" : f"Nominatim (pyosmium/{pyo_version.pyosmium_release})"}

            if self.session is not None:
                return self.session.get(url.get_full_url(),
                                       headers=headers, timeout=timeout or None,
                                       stream=True)

            @contextmanager
            def _get_url_with_session() -> Iterator[requests.Response]:
                with requests.Session() as session:
                    request = session.get(url.get_full_url(),
                                          headers=headers, timeout=timeout or None,
                                          stream=True)
                    yield request

            return _get_url_with_session()

        repl = ReplicationServer(url)
        setattr(repl, 'open_url', types.MethodType(patched_open_url, repl))

        return cast(ContextManager[ReplicationServer], repl)

    @contextmanager
    def get_cm() -> Generator[ReplicationServer, None, None]:
        yield ReplicationServer(url)

    return get_cm()
