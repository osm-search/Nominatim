# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for running the indexing.
"""
import itertools
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
                                                name HSTORE,
                                                class TEXT,
                                                type TEXT,
                                                linked_place_id BIGINT,
                                                rank_address SMALLINT,
                                                rank_search SMALLINT,
                                                indexed_status SMALLINT,
                                                indexed_date TIMESTAMP,
                                                partition SMALLINT,
                                                admin_level SMALLINT,
                                                country_code TEXT,
                                                address HSTORE,
                                                token_info JSONB,
                                                geometry_sector INTEGER)""")
            cur.execute("""CREATE TABLE location_property_osmline (
                               place_id BIGINT,
                               osm_id BIGINT,
                               address HSTORE,
                               token_info JSONB,
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
            cur.execute("DROP TYPE IF EXISTS prepare_update_info CASCADE")
            cur.execute("""CREATE TYPE prepare_update_info AS (
                             name HSTORE,
                             address HSTORE,
                             rank_address SMALLINT,
                             country_code TEXT,
                             class TEXT,
                             type TEXT,
                             linked_place_id BIGINT
                           )""")
            cur.execute("""CREATE OR REPLACE FUNCTION placex_indexing_prepare(p placex,
                                                     OUT result prepare_update_info)
                           AS $$
                           BEGIN
                             result.address := p.address;
                             result.name := p.name;
                             result.class := p.class;
                             result.type := p.type;
                             result.country_code := p.country_code;
                             result.rank_address := p.rank_address;
                           END;
                           $$ LANGUAGE plpgsql STABLE;
                        """)
            cur.execute("""CREATE OR REPLACE FUNCTION
                             get_interpolation_address(in_address HSTORE, wayid BIGINT)
                           RETURNS HSTORE AS $$
                           BEGIN
                             RETURN in_address;
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
                              (place_id, osm_id, indexed_status, geometry_sector)
                              VALUES (%s, %s, 1, %s)""",
                        (next_id, next_id, sector))
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
        return self.scalar("""SELECT count(*) from location_property_osmline
                              WHERE indexed_status > 0""")


@pytest.fixture
def test_db(temp_db_conn):
    yield IndexerTestDB(temp_db_conn)


@pytest.fixture
def test_tokenizer(tokenizer_mock, project_env):
    return factory.create_tokenizer(project_env)


@pytest.mark.parametrize("threads", [1, 15])
def test_index_all_by_rank(test_db, threads, test_tokenizer):
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert test_db.placex_unindexed() == 31
    assert test_db.osmline_unindexed() == 1

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_by_rank(0, 30)

    assert test_db.placex_unindexed() == 0
    assert test_db.osmline_unindexed() == 0

    assert test_db.scalar("""SELECT count(*) from placex
                             WHERE indexed_status = 0 and indexed_date is null""") == 0
    # ranks come in order of rank address
    assert test_db.scalar("""
        SELECT count(*) FROM placex p WHERE rank_address > 0
          AND indexed_date >= (SELECT min(indexed_date) FROM placex o
                               WHERE p.rank_address < o.rank_address)""") == 0
    # placex address ranked objects come before interpolations
    assert test_db.scalar(
        """SELECT count(*) FROM placex WHERE rank_address > 0
             AND indexed_date >
                   (SELECT min(indexed_date) FROM location_property_osmline)""") == 0
    # rank 0 comes after all other placex objects
    assert test_db.scalar(
        """SELECT count(*) FROM placex WHERE rank_address > 0
             AND indexed_date >
                   (SELECT min(indexed_date) FROM placex WHERE rank_address = 0)""") == 0


@pytest.mark.parametrize("threads", [1, 15])
def test_index_partial_without_30(test_db, threads, test_tokenizer):
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert test_db.placex_unindexed() == 31
    assert test_db.osmline_unindexed() == 1

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest',
                          test_tokenizer, threads)
    idx.index_by_rank(4, 15)

    assert test_db.placex_unindexed() == 19
    assert test_db.osmline_unindexed() == 1

    assert test_db.scalar("""
                    SELECT count(*) FROM placex
                      WHERE indexed_status = 0 AND not rank_address between 4 and 15""") == 0


@pytest.mark.parametrize("threads", [1, 15])
def test_index_partial_with_30(test_db, threads, test_tokenizer):
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert test_db.placex_unindexed() == 31
    assert test_db.osmline_unindexed() == 1

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_by_rank(28, 30)

    assert test_db.placex_unindexed() == 27
    assert test_db.osmline_unindexed() == 0

    assert test_db.scalar("""
                    SELECT count(*) FROM placex
                      WHERE indexed_status = 0 AND rank_address between 1 and 27""") == 0

@pytest.mark.parametrize("threads", [1, 15])
def test_index_boundaries(test_db, threads, test_tokenizer):
    for rank in range(4, 10):
        test_db.add_admin(rank_address=rank, rank_search=rank)
    for rank in range(31):
        test_db.add_place(rank_address=rank, rank_search=rank)
    test_db.add_osmline()

    assert test_db.placex_unindexed() == 37
    assert test_db.osmline_unindexed() == 1

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_boundaries(0, 30)

    assert test_db.placex_unindexed() == 31
    assert test_db.osmline_unindexed() == 1

    assert test_db.scalar("""
                    SELECT count(*) FROM placex
                      WHERE indexed_status = 0 AND class != 'boundary'""") == 0


@pytest.mark.parametrize("threads", [1, 15])
def test_index_postcodes(test_db, threads, test_tokenizer):
    for postcode in range(1000):
        test_db.add_postcode('de', postcode)
    for postcode in range(32000, 33000):
        test_db.add_postcode('us', postcode)

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_postcodes()

    assert test_db.scalar("""SELECT count(*) FROM location_postcode
                                  WHERE indexed_status != 0""") == 0


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

    assert test_db.placex_unindexed() == 0
    assert test_db.osmline_unindexed() == 0
    assert test_db.scalar("""SELECT count(*) FROM location_postcode
                             WHERE indexed_status != 0""") == 0


@pytest.mark.parametrize("threads", [1, 15])
def test_index_reopen_connection(test_db, threads, monkeypatch, test_tokenizer):
    monkeypatch.setattr(indexer.WorkerPool, "REOPEN_CONNECTIONS_AFTER", 15)

    for _ in range(1000):
        test_db.add_place(rank_address=30, rank_search=30)

    idx = indexer.Indexer('dbname=test_nominatim_python_unittest', test_tokenizer, threads)
    idx.index_by_rank(28, 30)

    assert test_db.placex_unindexed() == 0
