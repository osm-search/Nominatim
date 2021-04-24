"""
Tests for running the indexing.
"""
import itertools
import psycopg2
import pytest

from nominatim.indexer import indexer
from nominatim.tokenizer import factory

class IndexerTestDB:

    def __init__(self, conn):
        self.placex_id = itertools.count(100000)
        self.osmline_id = itertools.count(500000)
        self.postcode_id = itertools.count(700000)

        self.conn = conn
        self.conn.set_isolation_level(0)
        with self.conn.cursor() as cur:
            cur.execute('CREATE EXTENSION hstore')
            cur.execute("""CREATE TABLE placex (place_id BIGINT,
                                                class TEXT,
                                                type TEXT,
                                                rank_address SMALLINT,
                                                rank_search SMALLINT,
                                                indexed_status SMALLINT,
                                                indexed_date TIMESTAMP,
                                                partition SMALLINT,
                                                admin_level SMALLINT,
                                                address HSTORE,
                                                geometry_sector INTEGER)""")
            cur.execute("""CREATE TABLE location_property_osmline (
                               place_id BIGINT,
                               indexed_status SMALLINT,
                               indexed_date TIMESTAMP,
                               geometry_sector INTEGER)""")
            cur.execute("""CREATE TABLE location_postcode (
                               place_id BIGINT,
                               indexed_status SMALLINT,
                               indexed_date TIMESTAMP,
                               country_code varchar(2),
                               postcode TEXT)""")
            cur.execute("""CREATE OR REPLACE FUNCTION date_update() RETURNS TRIGGER
                           AS $$
                           BEGIN
                             IF NEW.indexed_status = 0 and OLD.indexed_status != 0 THEN
                               NEW.indexed_date = now();
                             END IF;
                             RETURN NEW;
                           END; $$ LANGUAGE plpgsql;""")
            cur.execute("""CREATE OR REPLACE FUNCTION placex_prepare_update(p placex,
                                                      OUT name HSTORE,
                                                      OUT address HSTORE,
                                                      OUT country_feature VARCHAR)
                           AS $$
                           BEGIN
                            address := p.address;
                            name := p.address;
                           END;
                           $$ LANGUAGE plpgsql STABLE;
                        """)
            for table in ('placex', 'location_property_osmline', 'location_postcode'):
                cur.execute("""CREATE TRIGGER {0}_update BEFORE UPDATE ON {0}
                               FOR EACH ROW EXECUTE PROCEDURE date_update()
                            """.format(table))

    def scalar(self, query):
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]

    def add_place(self, cls='place', typ='locality',
                  rank_search=30, rank_address=30, sector=20):
        next_id = next(self.placex_id)
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO placex
                              (place_id, class, type, rank_search, rank_address,
                               indexed_status, geometry_sector)
                              VALUES (%s, %s, %s, %s, %s, 1, %s)""",
                        (next_id, cls, typ, rank_search, rank_address, sector))
        return next_id

    def add_admin(self, **kwargs):
        kwargs['cls'] = 'boundary'
        kwargs['typ'] = 'administrative'
        return self.add_place(**kwargs)

    def add_osmline(self, sector=20):
        next_id = next(self.osmline_id)
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO location_property_osmline
                              (place_id, indexed_status, geometry_sector)
                              VALUES (%s, 1, %s)""",
                        (next_id, sector))
        return next_id

    def add_postcode(self, country, postcode):
        next_id = next(self.postcode_id)
        with self.conn.cursor() as cur:
            cur.execute("""INSERT INTO location_postcode
                            (place_id, indexed_status, country_code, postcode)
                            VALUES (%s, 1, %s, %s)""",
                        (next_id, country, postcode))
        return next_id

    def placex_unindexed(self):
        return self.scalar('SELECT count(*) from placex where indexed_status > 0')

    def osmline_unindexed(self):
        return self.scalar('SELECT count(*) from location_property_osmline where indexed_status > 0')


@pytest.fixture
def test_db(temp_db_conn):
    yield IndexerTestDB(temp_db_conn)


@pytest.fixture
def test_tokenizer(tokenizer_mock, def_config, tmp_path):
    def_config.project_dir = tmp_path
    return factory.create_tokenizer(def_config)


@pytest.mark.parametrize("threads", [1, 15])
def test_index_all_by_rank(test_db, threads, test_tokenizer):
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert 31 == test_db.placex_unindexed()
    assert 1 == test_db.osmline_unindexed()

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_by_rank(0, 30)

    assert 0 == test_db.placex_unindexed()
    assert 0 == test_db.osmline_unindexed()

    assert 0 == test_db.scalar("""SELECT count(*) from placex
                               WHERE indexed_status = 0 and indexed_date is null""")
    # ranks come in order of rank address
    assert 0 == test_db.scalar("""
        SELECT count(*) FROM placex p WHERE rank_address > 0
          AND indexed_date >= (SELECT min(indexed_date) FROM placex o
                               WHERE p.rank_address < o.rank_address)""")
    # placex rank < 30 objects come before interpolations
    assert 0 == test_db.scalar(
        """SELECT count(*) FROM placex WHERE rank_address < 30
             AND indexed_date > (SELECT min(indexed_date) FROM location_property_osmline)""")
    # placex rank = 30 objects come after interpolations
    assert 0 == test_db.scalar(
        """SELECT count(*) FROM placex WHERE rank_address = 30
             AND indexed_date < (SELECT max(indexed_date) FROM location_property_osmline)""")
    # rank 0 comes after rank 29 and before rank 30
    assert 0 == test_db.scalar(
        """SELECT count(*) FROM placex WHERE rank_address < 30
             AND indexed_date > (SELECT min(indexed_date) FROM placex WHERE rank_address = 0)""")
    assert 0 == test_db.scalar(
        """SELECT count(*) FROM placex WHERE rank_address = 30
             AND indexed_date < (SELECT max(indexed_date) FROM placex WHERE rank_address = 0)""")


@pytest.mark.parametrize("threads", [1, 15])
def test_index_partial_without_30(test_db, threads, test_tokenizer):
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert 31 == test_db.placex_unindexed()
    assert 1 == test_db.osmline_unindexed()

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest',
                          test_tokenizer, threads)
    idx.index_by_rank(4, 15)

    assert 19 == test_db.placex_unindexed()
    assert 1 == test_db.osmline_unindexed()

    assert 0 == test_db.scalar("""
                    SELECT count(*) FROM placex
                      WHERE indexed_status = 0 AND not rank_address between 4 and 15""")


@pytest.mark.parametrize("threads", [1, 15])
def test_index_partial_with_30(test_db, threads, test_tokenizer):
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert 31 == test_db.placex_unindexed()
    assert 1 == test_db.osmline_unindexed()

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_by_rank(28, 30)

    assert 27 == test_db.placex_unindexed()
    assert 0 == test_db.osmline_unindexed()

    assert 0 == test_db.scalar("""
                    SELECT count(*) FROM placex
                      WHERE indexed_status = 0 AND rank_address between 1 and 27""")

@pytest.mark.parametrize("threads", [1, 15])
def test_index_boundaries(test_db, threads, test_tokenizer):
    for rank in range(4, 10):
        test_db.add_admin(rank_address=rank, rank_search=rank)
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert 37 == test_db.placex_unindexed()
    assert 1 == test_db.osmline_unindexed()

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_boundaries(0, 30)

    assert 31 == test_db.placex_unindexed()
    assert 1 == test_db.osmline_unindexed()

    assert 0 == test_db.scalar("""
                    SELECT count(*) FROM placex
                      WHERE indexed_status = 0 AND class != 'boundary'""")


@pytest.mark.parametrize("threads", [1, 15])
def test_index_postcodes(test_db, threads, test_tokenizer):
    for postcode in range(1000):
        test_db.add_postcode('de', postcode)
    for postcode in range(32000, 33000):
        test_db.add_postcode('us', postcode)

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_postcodes()

    assert 0 == test_db.scalar("""SELECT count(*) FROM location_postcode
                                  WHERE indexed_status != 0""")


@pytest.mark.parametrize("analyse", [True, False])
def test_index_full(test_db, analyse, test_tokenizer):
    for rank in range(4, 10):
        test_db.add_admin(rank_address=rank, rank_search=rank)
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()
    for postcode in range(1000):
        test_db.add_postcode('de', postcode)

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, 4)
    idx.index_full(analyse=analyse)

    assert 0 == test_db.placex_unindexed()
    assert 0 == test_db.osmline_unindexed()
    assert 0 == test_db.scalar("""SELECT count(*) FROM location_postcode
                                  WHERE indexed_status != 0""")


@pytest.mark.parametrize("threads", [1, 15])
def test_index_reopen_connection(test_db, threads, monkeypatch, test_tokenizer):
    monkeypatch.setattr(indexer.WorkerPool, "REOPEN_CONNECTIONS_AFTER", 15)

    for _ in range(1000):
        test_db.add_place(rank_address=30, rank_search=30)

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_by_rank(28, 30)

    assert 0 == test_db.placex_unindexed()
