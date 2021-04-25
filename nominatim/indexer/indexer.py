"""
Main work horse for indexing (computing addresses) the database.
"""
import logging
import select

import psycopg2.extras

from nominatim.indexer.progress import ProgressLogger
from nominatim.indexer import runners
from nominatim.db.async_connection import DBConnection
from nominatim.db.connection import connect

LOG = logging.getLogger()

class WorkerPool:
    """ A pool of asynchronous database connections.

        The pool may be used as a context manager.
    """
    REOPEN_CONNECTIONS_AFTER = 100000

    def __init__(self, dsn, pool_size):
        self.threads = [DBConnection(dsn) for _ in range(pool_size)]
        self.free_workers = self._yield_free_worker()


    def finish_all(self):
        """ Wait for all connection to finish.
        """
        for thread in self.threads:
            while not thread.is_done():
                thread.wait()

        self.free_workers = self._yield_free_worker()

    def close(self):
        """ Close all connections and clear the pool.
        """
        for thread in self.threads:
            thread.close()
        self.threads = []
        self.free_workers = None


    def next_free_worker(self):
        """ Get the next free connection.
        """
        return next(self.free_workers)


    def _yield_free_worker(self):
        ready = self.threads
        command_stat = 0
        while True:
            for thread in ready:
                if thread.is_done():
                    command_stat += 1
                    yield thread

            if command_stat > self.REOPEN_CONNECTIONS_AFTER:
                for thread in self.threads:
                    while not thread.is_done():
                        thread.wait()
                    thread.connect()
                ready = self.threads
                command_stat = 0
            else:
                _, ready, _ = select.select([], self.threads, [])


    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        self.close()


class Indexer:
    """ Main indexing routine.
    """

    def __init__(self, dsn, tokenizer, num_threads):
        self.dsn = dsn
        self.tokenizer = tokenizer
        self.num_threads = num_threads


    def index_full(self, analyse=True):
        """ Index the complete database. This will first index boudnaries
            followed by all other objects. When `analyse` is True, then the
            database will be analysed at the appropriate places to
            ensure that database statistics are updated.
        """
        with connect(self.dsn) as conn:
            conn.autocommit = True

            if analyse:
                def _analyze():
                    with conn.cursor() as cur:
                        cur.execute('ANALYZE')
            else:
                def _analyze():
                    pass

            self.index_by_rank(0, 4)
            _analyze()

            self.index_boundaries(0, 30)
            _analyze()

            self.index_by_rank(5, 25)
            _analyze()

            self.index_by_rank(26, 30)
            _analyze()

            self.index_postcodes()
            _analyze()


    def index_boundaries(self, minrank, maxrank):
        """ Index only administrative boundaries within the given rank range.
        """
        LOG.warning("Starting indexing boundaries using %s threads",
                    self.num_threads)

        with self.tokenizer.name_analyzer() as analyzer:
            for rank in range(max(minrank, 4), min(maxrank, 26)):
                self._index(runners.BoundaryRunner(rank, analyzer))

    def index_by_rank(self, minrank, maxrank):
        """ Index all entries of placex in the given rank range (inclusive)
            in order of their address rank.

            When rank 30 is requested then also interpolations and
            places with address rank 0 will be indexed.
        """
        maxrank = min(maxrank, 30)
        LOG.warning("Starting indexing rank (%i to %i) using %i threads",
                    minrank, maxrank, self.num_threads)

        with self.tokenizer.name_analyzer() as analyzer:
            for rank in range(max(1, minrank), maxrank):
                self._index(runners.RankRunner(rank, analyzer))

            if maxrank == 30:
                self._index(runners.RankRunner(0, analyzer))
                self._index(runners.InterpolationRunner(analyzer), 20)
                self._index(runners.RankRunner(30, analyzer), 20)
            else:
                self._index(runners.RankRunner(maxrank, analyzer))


    def index_postcodes(self):
        """Index the entries ofthe location_postcode table.
        """
        LOG.warning("Starting indexing postcodes using %s threads", self.num_threads)

        self._index(runners.PostcodeRunner(), 20)


    def update_status_table(self):
        """ Update the status in the status table to 'indexed'.
        """
        with connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute('UPDATE import_status SET indexed = true')

            conn.commit()

    def _index(self, runner, batch=1):
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

                    with WorkerPool(self.dsn, self.num_threads) as pool:
                        while True:
                            places = cur.fetchmany(batch)
                            if not places:
                                break

                            LOG.debug("Processing places: %s", str(places))
                            worker = pool.next_free_worker()

                            runner.index_places(worker, places)
                            progress.add(len(places))

                        pool.finish_all()

                conn.commit()

        progress.done()
