"""
Functions for importing tiger data and handling tarbar and directory files
"""
import logging
import os
import tarfile
import selectors

from nominatim.db.connection import connect
from nominatim.db.async_connection import DBConnection
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


def handle_threaded_sql_statements(sel, file):
    """ Handles sql statement with multiplexing
    """

    lines = 0
    end_of_file = False
    # Using pool of database connections to execute sql statements
    while not end_of_file:
        for key, _ in sel.select(1):
            conn = key.data
            try:
                if conn.is_done():
                    sql_query = file.readline()
                    lines += 1
                    if not sql_query:
                        end_of_file = True
                        break
                    conn.perform(sql_query)
                    if lines == 1000:
                        print('. ', end='', flush=True)
                        lines = 0
            except Exception as exc: # pylint: disable=broad-except
                LOG.info('Wrong SQL statement: %s', exc)

def handle_unregister_connection_pool(sel, place_threads):
    """ Handles unregistering pool of connections
    """

    while place_threads > 0:
        for key, _ in sel.select(1):
            conn = key.data
            sel.unregister(conn)
            try:
                conn.wait()
            except Exception as exc: # pylint: disable=broad-except
                LOG.info('Wrong SQL statement: %s', exc)
            conn.close()
            place_threads -= 1

def add_tiger_data(dsn, data_dir, threads, config, sqllib_dir):
    """ Import tiger data from directory or tar file
    """

    sql_files, tar = handle_tarfile_or_directory(data_dir)

    if not sql_files:
        return

    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config, sqllib_dir)
        sql.run_sql_file(conn, 'tiger_import_start.sql')

    # Reading sql_files and then for each file line handling
    # sql_query in <threads - 1> chunks.
    sel = selectors.DefaultSelector()
    place_threads = max(1, threads - 1)

    # Creates a pool of database connections
    for _ in range(place_threads):
        conn = DBConnection(dsn)
        conn.connect()
        sel.register(conn, selectors.EVENT_WRITE, conn)

    for sql_file in sql_files:
        if not tar:
            file = open(sql_file)
        else:
            file = tar.extractfile(sql_file)

        handle_threaded_sql_statements(sel, file)

    # Unregistering pool of database connections
    handle_unregister_connection_pool(sel, place_threads)

    if tar:
        tar.close()
    print('\n')
    LOG.warning("Creating indexes on Tiger data")
    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config, sqllib_dir)
        sql.run_sql_file(conn, 'tiger_import_finish.sql')
