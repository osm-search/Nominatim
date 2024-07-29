# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
A connection pool that executes incoming queries in parallel.
"""
from typing import Any, Tuple, Optional
import asyncio
import logging
import time

import psycopg

LOG = logging.getLogger()

QueueItem = Optional[Tuple[psycopg.abc.Query, Any]]

class QueryPool:
    """ Pool to run SQL queries in parallel asynchronous execution.

        All queries are run in autocommit mode. If parallel execution leads
        to a deadlock, then the query is repeated.
        The results of the queries is discarded.
    """
    def __init__(self, dsn: str, pool_size: int = 1, **conn_args: Any) -> None:
        self.wait_time = 0.0
        self.query_queue: 'asyncio.Queue[QueueItem]' = asyncio.Queue(maxsize=2 * pool_size)

        self.pool = [asyncio.create_task(self._worker_loop(dsn, **conn_args))
                     for _ in range(pool_size)]


    async def put_query(self, query: psycopg.abc.Query, params: Any) -> None:
        """ Schedule a query for execution.
        """
        tstart = time.time()
        await self.query_queue.put((query, params))
        self.wait_time += time.time() - tstart
        await asyncio.sleep(0)


    async def finish(self) -> None:
        """ Wait for all queries to finish and close the pool.
        """
        for _ in self.pool:
            await self.query_queue.put(None)

        tstart = time.time()
        await asyncio.wait(self.pool)
        self.wait_time += time.time() - tstart

        for task in self.pool:
            excp = task.exception()
            if excp is not None:
                raise excp


    async def _worker_loop(self, dsn: str, **conn_args: Any) -> None:
        conn_args['autocommit'] = True
        aconn = await psycopg.AsyncConnection.connect(dsn, **conn_args)
        async with aconn:
            async with aconn.cursor() as cur:
                item = await self.query_queue.get()
                while item is not None:
                    try:
                        if item[1] is None:
                            await cur.execute(item[0])
                        else:
                            await cur.execute(item[0], item[1])

                        item = await self.query_queue.get()
                    except psycopg.errors.DeadlockDetected:
                        assert item is not None
                        LOG.info("Deadlock detected (sql = %s, params = %s), retry.",
                                 str(item[0]), str(item[1]))
                        # item is still valid here, causing a retry


    async def __aenter__(self) -> 'QueryPool':
        return self


    async def __aexit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        await self.finish()
