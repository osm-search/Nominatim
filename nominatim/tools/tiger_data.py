"""
Functions for importing tiger data and handling tarbar and directory files
"""
import logging
import os
import tarfile

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
        sql_files = [i for i in tar.getmembers() if i.name.endswith('.sql')]
        LOG.warning("Found %d SQL files in tarfile with path %s", len(sql_files), data_dir)
        if not sql_files:
            LOG.warning("Tiger data import selected but no files in tarfile's path %s", data_dir)
            return None, None
    else:
        files = os.listdir(data_dir)
        sql_files = [os.path.join(data_dir, i) for i in files if i.endswith('.sql')]
        LOG.warning("Found %d SQL files in path %s", len(sql_files), data_dir)
        if not sql_files:
            LOG.warning("Tiger data import selected but no files found in path %s", data_dir)
            return None, None

    return sql_files, tar


def handle_threaded_sql_statements(pool, file):
    """ Handles sql statement with multiplexing
    """

    lines = 0
    # Using pool of database connections to execute sql statements
    for sql_query in file:
        pool.next_free_worker().perform(sql_query)

        lines += 1
        if lines == 1000:
            print('.', end='', flush=True)
            lines = 0


def add_tiger_data(data_dir, config, threads):
    """ Import tiger data from directory or tar file `data dir`.
    """
    dsn = config.get_libpq_dsn()
    sql_files, tar = handle_tarfile_or_directory(data_dir)

    if not sql_files:
        return

    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config)
        sql.run_sql_file(conn, 'tiger_import_start.sql')

    # Reading sql_files and then for each file line handling
    # sql_query in <threads - 1> chunks.
    place_threads = max(1, threads - 1)

    with WorkerPool(dsn, place_threads, ignore_sql_errors=True) as pool:
        for sql_file in sql_files:
            if not tar:
                file = open(sql_file)
            else:
                file = tar.extractfile(sql_file)

            handle_threaded_sql_statements(pool, file)

    if tar:
        tar.close()
    print('\n')
    LOG.warning("Creating indexes on Tiger data")
    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config)
        sql.run_sql_file(conn, 'tiger_import_finish.sql')
