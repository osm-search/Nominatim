# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Main work horse for indexing (computing addresses) the database.
"""
from typing import Optional, Any, cast
import logging
import time

import psycopg2.extras

from nominatim.tokenizer.base import AbstractTokenizer
from nominatim.indexer.progress import ProgressLogger
from nominatim.indexer import runners
from nominatim.db.async_connection import DBConnection, WorkerPool
from nominatim.db.connection import connect, Connection, Cursor
from nominatim.typing import DictCursorResults

LOG = logging.getLogger()


class PlaceFetcher:
    """ Asynchronous connection that fetches place details for processing.
    """
    def __init__(self, dsn: str, setup_conn: Connection) -> None:
        self.wait_time = 0.0
        self.current_ids: Optional[DictCursorResults] = None
        self.conn: Optional[DBConnection] = DBConnection(dsn,
                                               cursor_factory=psycopg2.extras.DictCursor)

        with setup_conn.cursor() as cur:
            # need to fetch those manually because register_hstore cannot
            # fetch them on an asynchronous connection below.
            hstore_oid = cur.scalar("SELECT 'hstore'::regtype::oid")
            hstore_array_oid = cur.scalar("SELECT 'hstore[]'::regtype::oid")

        psycopg2.extras.register_hstore(self.conn.conn, oid=hstore_oid,
                                        array_oid=hstore_array_oid)

    def close(self) -> None:
        """ Close the underlying asynchronous connection.
        """
        if self.conn:
            self.conn.close()
            self.conn = None


    def fetch_next_batch(self, cur: Cursor, runner: runners.Runner) -> bool:
        """ Send a request for the next batch of places.
            If details for the places are required, they will be fetched
            asynchronously.

            Returns true if there is still data available.
        """
        ids = cast(Optional[DictCursorResults], cur.fetchmany(100))

        if not ids:
            self.current_ids = None
            return False

        assert self.conn is not None
        self.current_ids = runner.get_place_details(self.conn, ids)

        return True

    def get_batch(self) -> DictCursorResults:
        """ Get the next batch of data, previously requested with
            `fetch_next_batch`.
        """
        assert self.conn is not None
        assert self.conn.cursor is not None

        if self.current_ids is not None and not self.current_ids:
            tstart = time.time()
            self.conn.wait()
            self.wait_time += time.time() - tstart
            self.current_ids = cast(Optional[DictCursorResults],
                                    self.conn.cursor.fetchall())

        return self.current_ids if self.current_ids is not None else []

    def __enter__(self) -> 'PlaceFetcher':
        return self


    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        assert self.conn is not None
        self.conn.wait()
        self.close()


class Indexer:
    """ Main indexing routine.
    """

    def __init__(self, dsn: str, tokenizer: AbstractTokenizer, num_threads: int):
        self.dsn = dsn
        self.tokenizer = tokenizer
        self.num_threads = num_threads


    def has_pending(self) -> bool:
        """ Check if any data still needs indexing.
            This function must only be used after the import has finished.
            Otherwise it will be very expensive.
        """
        with connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 'a' FROM placex WHERE indexed_status > 0 LIMIT 1")
                return cur.rowcount > 0


    def index_full(self, analyse: bool = True) -> None:
        """ Index the complete database. This will first index boundaries
            followed by all other objects. When `analyse` is True, then the
            database will be analysed at the appropriate places to
            ensure that database statistics are updated.
        """
        with connect(self.dsn) as conn:
            conn.autocommit = True

            def _analyze() -> None:
                if analyse:
                    with conn.cursor() as cur:
                        cur.execute('ANALYZE')

            if self.index_by_rank(0, 4) > 0:
                _analyze()

            if self.index_boundaries(0, 30) > 100:
                _analyze()

            if self.index_by_rank(5, 25) > 100:
                _analyze()

            if self.index_by_rank(26, 30) > 1000:
                _analyze()

            if self.index_postcodes() > 100:
                _analyze()


    def index_boundaries(self, minrank: int, maxrank: int) -> int:
        """ Index only administrative boundaries within the given rank range.
        """
        total = 0
        LOG.warning("Starting indexing boundaries using %s threads",
                    self.num_threads)

        with self.tokenizer.name_analyzer() as analyzer:
            for rank in range(max(minrank, 4), min(maxrank, 26)):
                total += self._index(runners.BoundaryRunner(rank, analyzer))

        return total

    def index_by_rank(self, minrank: int, maxrank: int) -> int:
        """ Index all entries of placex in the given rank range (inclusive)
            in order of their address rank.

            When rank 30 is requested then also interpolations and
            places with address rank 0 will be indexed.
        """
        total = 0
        maxrank = min(maxrank, 30)
        LOG.warning("Starting indexing rank (%i to %i) using %i threads",
                    minrank, maxrank, self.num_threads)

        with self.tokenizer.name_analyzer() as analyzer:
            for rank in range(max(1, minrank), maxrank + 1):
                total += self._index(runners.RankRunner(rank, analyzer), 20 if rank == 30 else 1)

            if maxrank == 30:
                total += self._index(runners.RankRunner(0, analyzer))
                total += self._index(runners.InterpolationRunner(analyzer), 20)

        return total


    def index_postcodes(self) -> int:
        """Index the entries of the location_postcode table.
        """
        LOG.warning("Starting indexing postcodes using %s threads", self.num_threads)

        return self._index(runners.PostcodeRunner(), 20)


    def update_status_table(self) -> None:
        """ Update the status in the status table to 'indexed'.
        """
        with connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE import_status SET indexed = true')

            conn.commit()

    def _index(self, runner: runners.Runner, batch: int = 1) -> int:
        """ Index a single rank or table. `runner` describes the SQL to use
            for indexing. `batch` describes the number of objects that
            should be processed with a single SQL statement
        """
        LOG.warning("Starting %s (using batch size %s)", runner.name(), batch)

        with connect(self.dsn) as conn:
            psycopg2.extras.register_hstore(conn)
            with conn.cursor() as cur:
                total_tuples = cur.scalar(runner.sql_count_objects())
                LOG.debug("Total number of rows: %i", total_tuples)

            conn.commit()

            progress = ProgressLogger(runner.name(), total_tuples)

            if total_tuples > 0:
                with conn.cursor(name='places') as cur:
                    cur.execute(runner.sql_get_objects())

                    with PlaceFetcher(self.dsn, conn) as fetcher:
                        with WorkerPool(self.dsn, self.num_threads) as pool:
                            has_more = fetcher.fetch_next_batch(cur, runner)
                            while has_more:
                                places = fetcher.get_batch()

                                # asynchronously get the next batch
                                has_more = fetcher.fetch_next_batch(cur, runner)

                                # And insert the current batch
                                for idx in range(0, len(places), batch):
                                    part = places[idx:idx + batch]
                                    LOG.debug("Processing places: %s", str(part))
                                    runner.index_places(pool.next_free_worker(), part)
                                    progress.add(len(part))

                            LOG.info("Wait time: fetcher: %.2fs,  pool: %.2fs",
                                     fetcher.wait_time, pool.wait_time)

                conn.commit()

        return progress.done()
