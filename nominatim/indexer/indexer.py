"""
Main work horse for indexing (computing addresses) the database.
"""
import logging
import time

import psycopg2.extras

from nominatim.indexer.progress import ProgressLogger
from nominatim.indexer import runners
from nominatim.db.async_connection import DBConnection, WorkerPool
from nominatim.db.connection import connect

LOG = logging.getLogger()


class PlaceFetcher:
    """ Asynchronous connection that fetches place details for processing.
    """
    def __init__(self, dsn, setup_conn):
        self.wait_time = 0
        self.current_ids = None
        self.conn = DBConnection(dsn, cursor_factory=psycopg2.extras.DictCursor)

        with setup_conn.cursor() as cur:
            # need to fetch those manually because register_hstore cannot
            # fetch them on an asynchronous connection below.
            hstore_oid = cur.scalar("SELECT 'hstore'::regtype::oid")
            hstore_array_oid = cur.scalar("SELECT 'hstore[]'::regtype::oid")

        psycopg2.extras.register_hstore(self.conn.conn, oid=hstore_oid,
                                        array_oid=hstore_array_oid)

    def close(self):
        """ Close the underlying asynchronous connection.
        """
        if self.conn:
            self.conn.close()
            self.conn = None


    def fetch_next_batch(self, cur, runner):
        """ Send a request for the next batch of places.
            If details for the places are required, they will be fetched
            asynchronously.

            Returns true if there is still data available.
        """
        ids = cur.fetchmany(100)

        if not ids:
            self.current_ids = None
            return False

        if hasattr(runner, 'get_place_details'):
            runner.get_place_details(self.conn, ids)
            self.current_ids = []
        else:
            self.current_ids = ids

        return True

    def get_batch(self):
        """ Get the next batch of data, previously requested with
            `fetch_next_batch`.
        """
        if self.current_ids is not None and not self.current_ids:
            tstart = time.time()
            self.conn.wait()
            self.wait_time += time.time() - tstart
            self.current_ids = self.conn.cursor.fetchall()

        return self.current_ids

    def __enter__(self):
        return self


    def __exit__(self, exc_type, exc_value, traceback):
        self.conn.wait()
        self.close()


class Indexer:
    """ Main indexing routine.
    """

    def __init__(self, dsn, tokenizer, num_threads):
        self.dsn = dsn
        self.tokenizer = tokenizer
        self.num_threads = num_threads


    def index_full(self, analyse=True):
        """ Index the complete database. This will first index boundaries
            followed by all other objects. When `analyse` is True, then the
            database will be analysed at the appropriate places to
            ensure that database statistics are updated.
        """
        with connect(self.dsn) as conn:
            conn.autocommit = True

            def _analyze():
                if analyse:
                    with conn.cursor() as cur:
                        cur.execute('ANALYZE')

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

                    with PlaceFetcher(self.dsn, conn) as fetcher:
                        with WorkerPool(self.dsn, self.num_threads) as pool:
                            has_more = fetcher.fetch_next_batch(cur, runner)
                            while has_more:
                                places = fetcher.get_batch()

                                # asynchronously get the next batch
                                has_more = fetcher.fetch_next_batch(cur, runner)

                                # And insert the curent batch
                                for idx in range(0, len(places), batch):
                                    part = places[idx:idx+batch]
                                    LOG.debug("Processing places: %s", str(part))
                                    runner.index_places(pool.next_free_worker(), part)
                                    progress.add(len(part))

                            LOG.info("Wait time: fetcher: %.2fs,  pool: %.2fs",
                                     fetcher.wait_time, pool.wait_time)

                conn.commit()

        progress.done()
