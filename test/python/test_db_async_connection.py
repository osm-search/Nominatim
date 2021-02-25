"""
Tests for function providing a non-blocking query interface towards PostgreSQL.
"""
from contextlib import closing
import concurrent.futures

import pytest
import psycopg2
from psycopg2.extras import wait_select

from nominatim.db.async_connection import DBConnection, DeadlockHandler


@pytest.fixture
def conn(temp_db):
    with closing(DBConnection('dbname=' + temp_db)) as c:
        yield c


@pytest.fixture
def simple_conns(temp_db):
    conn1 = psycopg2.connect('dbname=' + temp_db)
    conn2 = psycopg2.connect('dbname=' + temp_db)

    yield conn1.cursor(), conn2.cursor()

    conn1.close()
    conn2.close()


def test_simple_query(conn, temp_db_conn):
    conn.connect()

    conn.perform('CREATE TABLE foo (id INT)')
    conn.wait()

    temp_db_conn.table_exists('foo')


def test_wait_for_query(conn):
    conn.connect()

    conn.perform('SELECT pg_sleep(1)')

    assert not conn.is_done()

    conn.wait()


def test_bad_query(conn):
    conn.connect()

    conn.perform('SELECT efasfjsea')

    with pytest.raises(psycopg2.ProgrammingError):
        conn.wait()


def exec_with_deadlock(cur, sql, detector):
    with DeadlockHandler(lambda *args: detector.append(1)):
        cur.execute(sql)


def test_deadlock(simple_conns):
    print(psycopg2.__version__)
    cur1, cur2 = simple_conns

    cur1.execute("""CREATE TABLE t1 (id INT PRIMARY KEY, t TEXT);
                    INSERT into t1 VALUES (1, 'a'), (2, 'b')""")
    cur1.connection.commit()

    cur1.execute("UPDATE t1 SET t = 'x' WHERE id = 1")
    cur2.execute("UPDATE t1 SET t = 'x' WHERE id = 2")

    # This is the tricky part of the test. The first SQL command runs into
    # a lock and blocks, so we have to run it in a separate thread. When the
    # second deadlocking SQL statement is issued, Postgresql will abort one of
    # the two transactions that cause the deadlock. There is no way to tell
    # which one of the two. Therefore wrap both in a DeadlockHandler and
    # expect that exactly one of the two triggers.
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        deadlock_check = []
        try:
            future = executor.submit(exec_with_deadlock, cur2,
                                     "UPDATE t1 SET t = 'y' WHERE id = 1",
                                     deadlock_check)

            while not future.running():
                pass


            exec_with_deadlock(cur1, "UPDATE t1 SET t = 'y' WHERE id = 2",
                               deadlock_check)
        finally:
            # Whatever happens, make sure the deadlock gets resolved.
            cur1.connection.rollback()

        future.result()

        assert len(deadlock_check) == 1


