"""
Tests for maintenance and analysis functions.
"""
import pytest

from nominatim.db.connection import connect
from nominatim.errors import UsageError
from nominatim.tools import admin

@pytest.fixture
def db(temp_db, placex_table):
    conn = connect('dbname=' + temp_db)
    yield conn
    conn.close()

def test_analyse_indexing_no_objects(db):
    with pytest.raises(UsageError):
        admin.analyse_indexing(db)


@pytest.mark.parametrize("oid", ['1234', 'N123a', 'X123'])
def test_analyse_indexing_bad_osmid(db, oid):
    with pytest.raises(UsageError):
        admin.analyse_indexing(db, osm_id=oid)


def test_analyse_indexing_unknown_osmid(db):
    with pytest.raises(UsageError):
        admin.analyse_indexing(db, osm_id='W12345674')


def test_analyse_indexing_with_place_id(db, temp_db_cursor):
    temp_db_cursor.execute("INSERT INTO placex (place_id) VALUES(12345)")

    admin.analyse_indexing(db, place_id=12345)


def test_analyse_indexing_with_osm_id(db, temp_db_cursor):
    temp_db_cursor.execute("""INSERT INTO placex (place_id, osm_type, osm_id)
                              VALUES(9988, 'N', 10000)""")

    admin.analyse_indexing(db, osm_id='N10000')
