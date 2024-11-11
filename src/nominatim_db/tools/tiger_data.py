# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2024 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Functions for importing tiger data and handling tarbar and directory files
"""
from typing import Any, TextIO, List, Union, cast, Iterator, Dict
import csv
import io
import logging
import os
import tarfile

from psycopg.types.json import Json

from ..config import Configuration
from ..db.connection import connect
from ..db.sql_preprocessor import SQLPreprocessor
from ..errors import UsageError
from ..db.query_pool import QueryPool
from ..data.place_info import PlaceInfo
from ..tokenizer.base import AbstractTokenizer
from . import freeze

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
                self.tar_handle = tarfile.open(data_dir)
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

    def __bool__(self) -> bool:
        return bool(self.files)

    def get_file(self, fname: Union[str, tarfile.TarInfo]) -> TextIO:
        """ Return a file handle to the next file to be processed.
            Raises an IndexError if there is no file left.
        """
        if self.tar_handle is not None:
            extracted = self.tar_handle.extractfile(fname)
            assert extracted is not None
            return io.TextIOWrapper(extracted)

        return open(cast(str, fname), encoding='utf-8')

    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """ Iterate over the lines in each file.
        """
        for fname in self.files:
            fd = self.get_file(fname)
            yield from csv.DictReader(fd, delimiter=';')


async def add_tiger_data(data_dir: str, config: Configuration, threads: int,
                         tokenizer: AbstractTokenizer) -> int:
    """ Import tiger data from directory or tar file `data dir`.
    """
    dsn = config.get_libpq_dsn()

    with connect(dsn) as conn:
        if freeze.is_frozen(conn):
            raise UsageError("Tiger cannot be imported when database frozen (Github issue #3048)")

    with TigerInput(data_dir) as tar:
        if not tar:
            return 1

        with connect(dsn) as conn:
            sql = SQLPreprocessor(conn, config)
            sql.run_sql_file(conn, 'tiger_import_start.sql')

        # Reading files and then for each file line handling
        # sql_query in <threads - 1> chunks.
        place_threads = max(1, threads - 1)

        async with QueryPool(dsn, place_threads, autocommit=True) as pool:
            with tokenizer.name_analyzer() as analyzer:
                lines = 0
                for row in tar:
                    try:
                        address = dict(street=row['street'], postcode=row['postcode'])
                        args = ('SRID=4326;' + row['geometry'],
                                int(row['from']), int(row['to']), row['interpolation'],
                                Json(analyzer.process_place(PlaceInfo({'address': address}))),
                                analyzer.normalize_postcode(row['postcode']))
                    except ValueError:
                        continue

                    await pool.put_query(
                        """SELECT tiger_line_import(%s::GEOMETRY, %s::INT,
                                                    %s::INT, %s::TEXT, %s::JSONB, %s::TEXT)""",
                        args)

                    lines += 1
                    if lines == 1000:
                        print('.', end='', flush=True)
                    lines = 0

        print('', flush=True)

    LOG.warning("Creating indexes on Tiger data")
    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config)
        sql.run_sql_file(conn, 'tiger_import_finish.sql')

    return 0
