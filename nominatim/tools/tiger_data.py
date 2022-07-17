# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing tiger data and handling tarbar and directory files
"""
from typing import Any, TextIO, List, Union, cast
import csv
import io
import logging
import os
import tarfile

from psycopg2.extras import Json

from nominatim.config import Configuration
from nominatim.db.connection import connect
from nominatim.db.async_connection import WorkerPool
from nominatim.db.sql_preprocessor import SQLPreprocessor
from nominatim.errors import UsageError
from nominatim.data.place_info import PlaceInfo
from nominatim.tokenizer.base import AbstractAnalyzer, AbstractTokenizer

LOG = logging.getLogger()

class TigerInput:
    """ Context manager that goes through Tiger input files which may
        either be in a directory or gzipped together in a tar file.
    """

    def __init__(self, data_dir: str) -> None:
        self.tar_handle = None
        self.files: List[Union[str, tarfile.TarInfo]] = []

        if data_dir.endswith('.tar.gz'):
            try:
                self.tar_handle = tarfile.open(data_dir) # pylint: disable=consider-using-with
            except tarfile.ReadError as err:
                LOG.fatal("Cannot open '%s'. Is this a tar file?", data_dir)
                raise UsageError("Cannot open Tiger data file.") from err

            self.files = [i for i in self.tar_handle.getmembers() if i.name.endswith('.csv')]
            LOG.warning("Found %d CSV files in tarfile with path %s", len(self.files), data_dir)
        else:
            files = os.listdir(data_dir)
            self.files = [os.path.join(data_dir, i) for i in files if i.endswith('.csv')]
            LOG.warning("Found %d CSV files in path %s", len(self.files), data_dir)

        if not self.files:
            LOG.warning("Tiger data import selected but no files found at %s", data_dir)


    def __enter__(self) -> 'TigerInput':
        return self


    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.tar_handle:
            self.tar_handle.close()
            self.tar_handle = None


    def next_file(self) -> TextIO:
        """ Return a file handle to the next file to be processed.
            Raises an IndexError if there is no file left.
        """
        fname = self.files.pop(0)

        if self.tar_handle is not None:
            extracted = self.tar_handle.extractfile(fname)
            assert extracted is not None
            return io.TextIOWrapper(extracted)

        return open(cast(str, fname), encoding='utf-8')


    def __len__(self) -> int:
        return len(self.files)


def handle_threaded_sql_statements(pool: WorkerPool, fd: TextIO,
                                   analyzer: AbstractAnalyzer) -> None:
    """ Handles sql statement with multiplexing
    """
    lines = 0
    # Using pool of database connections to execute sql statements

    sql = "SELECT tiger_line_import(%s, %s, %s, %s, %s, %s)"

    for row in csv.DictReader(fd, delimiter=';'):
        try:
            address = dict(street=row['street'], postcode=row['postcode'])
            args = ('SRID=4326;' + row['geometry'],
                    int(row['from']), int(row['to']), row['interpolation'],
                    Json(analyzer.process_place(PlaceInfo({'address': address}))),
                    analyzer.normalize_postcode(row['postcode']))
        except ValueError:
            continue
        pool.next_free_worker().perform(sql, args=args)

        lines += 1
        if lines == 1000:
            print('.', end='', flush=True)
            lines = 0


def add_tiger_data(data_dir: str, config: Configuration, threads: int,
                   tokenizer: AbstractTokenizer) -> int:
    """ Import tiger data from directory or tar file `data dir`.
    """
    dsn = config.get_libpq_dsn()

    with TigerInput(data_dir) as tar:
        if not tar:
            return 1

        with connect(dsn) as conn:
            sql = SQLPreprocessor(conn, config)
            sql.run_sql_file(conn, 'tiger_import_start.sql')

        # Reading files and then for each file line handling
        # sql_query in <threads - 1> chunks.
        place_threads = max(1, threads - 1)

        with WorkerPool(dsn, place_threads, ignore_sql_errors=True) as pool:
            with tokenizer.name_analyzer() as analyzer:
                while tar:
                    with tar.next_file() as fd:
                        handle_threaded_sql_statements(pool, fd, analyzer)

        print('\n')

    LOG.warning("Creating indexes on Tiger data")
    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config)
        sql.run_sql_file(conn, 'tiger_import_finish.sql')

    return 0
