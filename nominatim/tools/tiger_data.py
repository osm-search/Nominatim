"""
Functions for importing tiger data and handling tarbar and directory files
"""
import csv
import io
import logging
import os
import tarfile

import psycopg2.extras

from nominatim.db.connection import connect
from nominatim.db.async_connection import WorkerPool
from nominatim.db.sql_preprocessor import SQLPreprocessor


LOG = logging.getLogger()


def handle_tarfile_or_directory(data_dir):
    """ Handles tarfile or directory for importing tiger data
    """

    tar = None
    if data_dir.endswith('.tar.gz'):
        tar = tarfile.open(data_dir)
        csv_files = [i for i in tar.getmembers() if i.name.endswith('.csv')]
        LOG.warning("Found %d CSV files in tarfile with path %s", len(csv_files), data_dir)
        if not csv_files:
            LOG.warning("Tiger data import selected but no files in tarfile's path %s", data_dir)
            return None, None
    else:
        files = os.listdir(data_dir)
        csv_files = [os.path.join(data_dir, i) for i in files if i.endswith('.csv')]
        LOG.warning("Found %d CSV files in path %s", len(csv_files), data_dir)
        if not csv_files:
            LOG.warning("Tiger data import selected but no files found in path %s", data_dir)
            return None, None

    return csv_files, tar


def handle_threaded_sql_statements(pool, fd, analyzer):
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
                    psycopg2.extras.Json(analyzer.process_place(dict(address=address))),
                    analyzer.normalize_postcode(row['postcode']))
        except ValueError:
            continue
        pool.next_free_worker().perform(sql, args=args)

        lines += 1
        if lines == 1000:
            print('.', end='', flush=True)
            lines = 0


def add_tiger_data(data_dir, config, threads, tokenizer):
    """ Import tiger data from directory or tar file `data dir`.
    """
    dsn = config.get_libpq_dsn()
    files, tar = handle_tarfile_or_directory(data_dir)

    if not files:
        return

    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config)
        sql.run_sql_file(conn, 'tiger_import_start.sql')

    # Reading files and then for each file line handling
    # sql_query in <threads - 1> chunks.
    place_threads = max(1, threads - 1)

    with WorkerPool(dsn, place_threads, ignore_sql_errors=True) as pool:
        with tokenizer.name_analyzer() as analyzer:
            for fname in files:
                if not tar:
                    fd = open(fname)
                else:
                    fd = io.TextIOWrapper(tar.extractfile(fname))

                handle_threaded_sql_statements(pool, fd, analyzer)

                fd.close()

    if tar:
        tar.close()
    print('\n')
    LOG.warning("Creating indexes on Tiger data")
    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config)
        sql.run_sql_file(conn, 'tiger_import_finish.sql')
