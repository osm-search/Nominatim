"""
Functions for setting up and importing a new Nominatim database.
"""
import logging
import os
import tarfile
import selectors

from ..db.connection import connect
from ..db.async_connection import DBConnection
from ..db.sql_preprocessor import SQLPreprocessor

# pylint: disable=R0912
# pylint: disable=R0914,R0915,W0702

LOG = logging.getLogger()


def add_tiger_data(dsn, data_dir, threads, config, sqllib_dir):
    """ Import tiger data from directory or tar file
    """
    # Handling directory or tarball file.
    is_tarfile = False
    if data_dir.endswith('.tar.gz'):
        is_tarfile = True
        tar = tarfile.open(data_dir)
        sql_files = [i for i in tar.getmembers() if i.name.endswith('.sql')]
        LOG.warning("Found %d SQL files in tarfile with path %s", len(sql_files), data_dir)
        if not sql_files:
            LOG.warning("Tiger data import selected but no files in tarfile's path %s", data_dir)
            return
    else:
        files = os.listdir(data_dir)
        sql_files = [i for i in files if i.endswith('.sql')]
        LOG.warning("Found %d SQL files in path %s", len(sql_files), data_dir)
        if not sql_files:
            LOG.warning("Tiger data import selected but no files found in path %s", data_dir)
            return

    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config, sqllib_dir)
        sql.run_sql_file(conn, 'tiger_import_start.sql')

    # Reading sql_files and then for each file line handling
    # sql_query in <threads - 1> chunks.
    sel = selectors.DefaultSelector()
    place_threads = max(1, threads - 1)
    for sql_file in sql_files:
        if not is_tarfile:
            file_path = os.path.join(data_dir, sql_file)
            file = open(file_path)
        else:
            file = tar.extractfile(sql_file)
        lines = 0
        end_of_file = False
        total_used_threads = place_threads
        while True:
            if end_of_file:
                break
            for imod in range(place_threads):
                conn = DBConnection(dsn)
                conn.connect()

                sql_query = file.readline()
                lines += 1

                if not sql_query:
                    end_of_file = True
                    total_used_threads = imod
                    break

                conn.perform(sql_query)
                sel.register(conn, selectors.EVENT_READ, conn)

                if lines == 1000:
                    print('. ', end='', flush=True)
                    lines = 0

            todo = min(place_threads, total_used_threads)
            while todo > 0:
                for key, _ in sel.select(1):
                    try:
                        conn = key.data
                        sel.unregister(conn)
                        conn.wait()
                        conn.close()
                        todo -= 1
                    except:
                        todo -= 1

    if is_tarfile:
        tar.close()
    print('\n')
    LOG.warning("Creating indexes on Tiger data")
    with connect(dsn) as conn:
        sql = SQLPreprocessor(conn, config, sqllib_dir)
        sql.run_sql_file(conn, 'tiger_import_finish.sql')
    