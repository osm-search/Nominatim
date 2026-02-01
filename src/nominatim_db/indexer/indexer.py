# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Main work horse for indexing (computing addresses) the database.
"""
from typing import cast, List, Any, Optional
import logging
import time

import psycopg

from ..db.connection import connect, execute_scalar
from ..db.query_pool import QueryPool
from ..tokenizer.base import AbstractTokenizer
from .progress import ProgressLogger
from . import runners

LOG = logging.getLogger()


class Indexer:
    """ Main indexing routine.
    """

    def __init__(self, dsn: str, tokenizer: AbstractTokenizer, num_threads: int):
        self.dsn = dsn
        self.tokenizer = tokenizer
        self.num_threads = num_threads

    def has_pending(self, minrank: int = 0, maxrank: int = 30) -> bool:
        """ Check if any data still needs indexing.
            This function must only be used after the import has finished.
            Otherwise it will be very expensive.
        """
        with connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(""" SELECT 'a'
                                 FROM placex
                                WHERE rank_address BETWEEN %s AND %s
                                  AND indexed_status > 0
                                LIMIT 1""",
                            (minrank, maxrank))
                return cur.rowcount > 0

    async def index_full(self, analyse: bool = True) -> None:
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

            while True:
                if await self.index_by_rank(0, 4) > 0:
                    _analyze()

                if await self.index_boundaries(0, 30) > 100:
                    _analyze()

                if await self.index_by_rank(5, 25) > 100:
                    _analyze()

                if await self.index_by_rank(26, 30) > 1000:
                    _analyze()

                if await self.index_postcodes() > 100:
                    _analyze()

                if not self.has_pending():
                    break

    async def index_boundaries(self, minrank: int, maxrank: int) -> int:
        """ Index only administrative boundaries within the given rank range.
        """
        total = 0
        LOG.warning("Starting indexing boundaries using %s threads",
                    self.num_threads)

        minrank = max(minrank, 4)
        maxrank = min(maxrank, 25)

        # Precompute number of rows to process for all rows
        with connect(self.dsn) as conn:
            hstore_info = psycopg.types.TypeInfo.fetch(conn, "hstore")
            if hstore_info is None:
                raise RuntimeError('Hstore extension is requested but not installed.')
            psycopg.types.hstore.register_hstore(hstore_info)

            with conn.cursor() as cur:
                cur = conn.execute(""" SELECT rank_search, count(*)
                                       FROM placex
                                       WHERE rank_search between %s and %s
                                             AND class = 'boundary' and type = 'administrative'
                                             AND indexed_status > 0
                                       GROUP BY rank_search""",
                                   (minrank, maxrank))
                total_tuples = {row.rank_search: row.count for row in cur}

        with self.tokenizer.name_analyzer() as analyzer:
            for rank in range(minrank, maxrank + 1):
                total += await self._index(runners.BoundaryRunner(rank, analyzer),
                                           total_tuples=total_tuples.get(rank, 0))

        return total

    async def index_by_rank(self, minrank: int, maxrank: int) -> int:
        """ Index all entries of placex in the given rank range (inclusive)
            in order of their address rank.

            When rank 30 is requested then also interpolations and
            places with address rank 0 will be indexed.
        """
        total = 0
        maxrank = min(maxrank, 30)
        LOG.warning("Starting indexing rank (%i to %i) using %i threads",
                    minrank, maxrank, self.num_threads)

        # Precompute number of rows to process for all rows
        with connect(self.dsn) as conn:
            hstore_info = psycopg.types.TypeInfo.fetch(conn, "hstore")
            if hstore_info is None:
                raise RuntimeError('Hstore extension is requested but not installed.')
            psycopg.types.hstore.register_hstore(hstore_info)

            with conn.cursor() as cur:
                cur = conn.execute(""" SELECT rank_address, count(*)
                                       FROM placex
                                       WHERE rank_address between %s and %s
                                             AND indexed_status > 0
                                       GROUP BY rank_address""",
                                   (minrank, maxrank))
                total_tuples = {row.rank_address: row.count for row in cur}

        with self.tokenizer.name_analyzer() as analyzer:
            for rank in range(max(0, minrank), maxrank + 1):
                if rank >= 30:
                    batch = 20
                elif rank >= 26:
                    batch = 5
                else:
                    batch = 1
                total += await self._index(runners.RankRunner(rank, analyzer),
                                           batch=batch, total_tuples=total_tuples.get(rank, 0))

            if maxrank == 30:
                total += await self._index(runners.RankRunner(0, analyzer))
                total += await self._index(runners.InterpolationRunner(analyzer), batch=20)

        return total

    async def index_postcodes(self) -> int:
        """Index the entries of the location_postcodes table.
        """
        LOG.warning("Starting indexing postcodes using %s threads", self.num_threads)

        return await self._index(runners.PostcodeRunner(), batch=20)

    def update_status_table(self) -> None:
        """ Update the status in the status table to 'indexed'.
        """
        with connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE import_status SET indexed = true')

            conn.commit()

    async def _index(self, runner: runners.Runner, batch: int = 1,
                     total_tuples: Optional[int] = None) -> int:
        """ Index a single rank or table. `runner` describes the SQL to use
            for indexing. `batch` describes the number of objects that
            should be processed with a single SQL statement.

            `total_tuples` may contain the total number of rows to process.
            When not supplied, the value will be computed using the
            appropriate runner function.
        """
        LOG.warning("Starting %s (using batch size %s)", runner.name(), batch)

        if total_tuples is None:
            total_tuples = self._prepare_indexing(runner)

        progress = ProgressLogger(runner.name(), total_tuples)

        if total_tuples > 0:
            async with await psycopg.AsyncConnection.connect(
                                 self.dsn, row_factory=psycopg.rows.dict_row) as aconn, \
                       QueryPool(self.dsn, self.num_threads, autocommit=True) as pool:
                fetcher_time = 0.0
                tstart = time.time()
                async with aconn.cursor(name='places') as cur:
                    query = runner.index_places_query(batch)
                    params: List[Any] = []
                    num_places = 0
                    async for place in cur.stream(runner.sql_get_objects()):
                        fetcher_time += time.time() - tstart

                        params.extend(runner.index_places_params(place))
                        num_places += 1

                        if num_places >= batch:
                            LOG.debug("Processing places: %s", str(params))
                            await pool.put_query(query, params)
                            progress.add(num_places)
                            params = []
                            num_places = 0

                        tstart = time.time()

                if num_places > 0:
                    await pool.put_query(runner.index_places_query(num_places), params)

            LOG.info("Wait time: fetcher: %.2fs,  pool: %.2fs",
                     fetcher_time, pool.wait_time)

        return progress.done()

    def _prepare_indexing(self, runner: runners.Runner) -> int:
        with connect(self.dsn) as conn:
            hstore_info = psycopg.types.TypeInfo.fetch(conn, "hstore")
            if hstore_info is None:
                raise RuntimeError('Hstore extension is requested but not installed.')
            psycopg.types.hstore.register_hstore(hstore_info)

            total_tuples = execute_scalar(conn, runner.sql_count_objects())
            LOG.debug("Total number of rows: %i", total_tuples)
        return cast(int, total_tuples)
