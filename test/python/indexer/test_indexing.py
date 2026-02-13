#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Tests for running the indexing.
"""

import pytest
import pytest_asyncio  # noqa

from nominatim_db.indexer import indexer
from nominatim_db.tokenizer import factory


class TestIndexing:
    @pytest.fixture(autouse=True)
    def setup(self, temp_db_conn, project_env, tokenizer_mock,
              placex_table, postcode_table, osmline_table):
        self.conn = temp_db_conn
        temp_db_conn.execute("""
            CREATE OR REPLACE FUNCTION date_update() RETURNS TRIGGER AS $$
            BEGIN
              IF NEW.indexed_status = 0 and OLD.indexed_status != 0 THEN
                NEW.indexed_date = now();
              END IF;
              RETURN NEW;
            END; $$ LANGUAGE plpgsql;

            DROP TYPE IF EXISTS prepare_update_info CASCADE;
            CREATE TYPE prepare_update_info AS (
                         name HSTORE,
                         address HSTORE,
                         rank_address SMALLINT,
                         country_code TEXT,
                         class TEXT,
                         type TEXT,
                         linked_place_id BIGINT
                       );
            CREATE OR REPLACE FUNCTION placex_indexing_prepare(p placex,
                                                 OUT result prepare_update_info) AS $$
            BEGIN
              result.address := p.address;
              result.name := p.name;
              result.class := p.class;
              result.type := p.type;
              result.country_code := p.country_code;
              result.rank_address := p.rank_address;
            END; $$ LANGUAGE plpgsql STABLE;

            CREATE OR REPLACE FUNCTION get_interpolation_address(in_address HSTORE, wayid BIGINT)
            RETURNS HSTORE AS $$ SELECT in_address $$ LANGUAGE sql STABLE;
        """)

        for table in ('placex', 'location_property_osmline', 'location_postcodes'):
            temp_db_conn.execute("""CREATE TRIGGER {0}_update BEFORE UPDATE ON {0}
                                    FOR EACH ROW EXECUTE PROCEDURE date_update()
                                 """.format(table))

        self.tokenizer = factory.create_tokenizer(project_env)

    def scalar(self, query):
        with self.conn.cursor() as cur:
            cur.execute(query)
            return cur.fetchone()[0]

    def placex_unindexed(self):
        return self.scalar('SELECT count(*) from placex where indexed_status > 0')

    def osmline_unindexed(self):
        return self.scalar("""SELECT count(*) from location_property_osmline
                              WHERE indexed_status > 0""")

    @pytest.mark.parametrize("threads", [1, 15])
    @pytest.mark.asyncio
    async def test_index_all_by_rank(self, dsn, threads, placex_row, osmline_row):
        for rank in range(31):
            placex_row(rank_address=rank, rank_search=rank, indexed_status=1)
        osmline_row()

        assert self.placex_unindexed() == 31
        assert self.osmline_unindexed() == 1

        idx = indexer.Indexer(dsn, self.tokenizer, threads)
        await idx.index_by_rank(0, 30)

        assert self.placex_unindexed() == 0
        assert self.osmline_unindexed() == 0

        assert self.scalar("""SELECT count(*) from placex
                                 WHERE indexed_status = 0 and indexed_date is null""") == 0
        # ranks come in order of rank address
        assert self.scalar("""
            SELECT count(*) FROM placex p WHERE rank_address > 0
              AND indexed_date >= (SELECT min(indexed_date) FROM placex o
                                   WHERE p.rank_address < o.rank_address)""") == 0
        # placex address ranked objects come before interpolations
        assert self.scalar(
            """SELECT count(*) FROM placex WHERE rank_address > 0
                 AND indexed_date >
                       (SELECT min(indexed_date) FROM location_property_osmline)""") == 0
        # rank 0 comes after all other placex objects
        assert self.scalar(
            """SELECT count(*) FROM placex WHERE rank_address > 0
                 AND indexed_date >
                       (SELECT min(indexed_date) FROM placex WHERE rank_address = 0)""") == 0

    @pytest.mark.parametrize("threads", [1, 15])
    @pytest.mark.asyncio
    async def test_index_partial_without_30(self, dsn, threads, placex_row, osmline_row):
        for rank in range(31):
            placex_row(rank_address=rank, rank_search=rank, indexed_status=1)
        osmline_row()

        assert self.placex_unindexed() == 31
        assert self.osmline_unindexed() == 1

        idx = indexer.Indexer(dsn, self.tokenizer, threads)
        await idx.index_by_rank(4, 15)

        assert self.placex_unindexed() == 19
        assert self.osmline_unindexed() == 1

        assert self.scalar("""
                        SELECT count(*) FROM placex
                          WHERE indexed_status = 0 AND not rank_address between 4 and 15""") == 0

    @pytest.mark.parametrize("threads", [1, 15])
    @pytest.mark.asyncio
    async def test_index_partial_with_30(self, dsn, threads, placex_row, osmline_row):
        for rank in range(31):
            placex_row(rank_address=rank, rank_search=rank, indexed_status=1)
        osmline_row()

        assert self.placex_unindexed() == 31
        assert self.osmline_unindexed() == 1

        idx = indexer.Indexer(dsn, self.tokenizer, threads)
        await idx.index_by_rank(28, 30)

        assert self.placex_unindexed() == 28
        assert self.osmline_unindexed() == 0

        assert self.scalar("""
                        SELECT count(*) FROM placex
                          WHERE indexed_status = 0 AND rank_address between 0 and 27""") == 0

    @pytest.mark.parametrize("threads", [1, 15])
    @pytest.mark.asyncio
    async def test_index_boundaries(self, dsn, threads, placex_row, osmline_row):
        for rank in range(4, 10):
            placex_row(cls='boundary', typ='administrative',
                       rank_address=rank, rank_search=rank, indexed_status=1)
        for rank in range(31):
            placex_row(rank_address=rank, rank_search=rank, indexed_status=1)
        osmline_row()

        assert self.placex_unindexed() == 37
        assert self.osmline_unindexed() == 1

        idx = indexer.Indexer(dsn, self.tokenizer, threads)
        await idx.index_boundaries()

        assert self.placex_unindexed() == 31
        assert self.osmline_unindexed() == 1

        assert self.scalar("""
                        SELECT count(*) FROM placex
                          WHERE indexed_status = 0 AND class != 'boundary'""") == 0

    @pytest.mark.parametrize("threads", [1, 15])
    @pytest.mark.asyncio
    async def test_index_postcodes(self, dsn, threads, postcode_row):
        for postcode in range(1000):
            postcode_row(country='de', postcode=postcode)
        for postcode in range(32000, 33000):
            postcode_row(country='us', postcode=postcode)

        idx = indexer.Indexer(dsn, self.tokenizer, threads)
        await idx.index_postcodes()

        assert self.scalar("""SELECT count(*) FROM location_postcodes
                                      WHERE indexed_status != 0""") == 0

    @pytest.mark.parametrize("analyse", [True, False])
    @pytest.mark.asyncio
    async def test_index_full(self, dsn, analyse, placex_row, osmline_row, postcode_row):
        for rank in range(4, 10):
            placex_row(cls='boundary', typ='administrative',
                       rank_address=rank, rank_search=rank, indexed_status=1)
        for rank in range(31):
            placex_row(rank_address=rank, rank_search=rank, indexed_status=1)
        osmline_row()
        for postcode in range(1000):
            postcode_row(country='de', postcode=postcode)

        idx = indexer.Indexer(dsn, self.tokenizer, 4)
        await idx.index_full(analyse=analyse)

        assert self.placex_unindexed() == 0
        assert self.osmline_unindexed() == 0
        assert self.scalar("""SELECT count(*) FROM location_postcodes
                                 WHERE indexed_status != 0""") == 0
