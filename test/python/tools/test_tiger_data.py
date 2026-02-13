# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for tiger data function
"""
import tarfile
from textwrap import dedent

import pytest
import pytest_asyncio  # noqa: F401

from nominatim_db.tools import tiger_data
from nominatim_db.errors import UsageError


@pytest.fixture
def csv_factory(tmp_path):
    def _mk_file(fname, hnr_from=1, hnr_to=9, interpol='odd', street='Main St',
                 city='Newtown', state='AL', postcode='12345',
                 geometry='LINESTRING(-86.466995 32.428956,-86.466923 32.428933)'):
        (tmp_path / (fname + '.csv')).write_text(dedent("""\
        from;to;interpolation;street;city;state;postcode;geometry
        {};{};{};{};{};{};{};{}
        """.format(hnr_from, hnr_to, interpol, street, city, state,
                   postcode, geometry)), encoding='utf-8')

    return _mk_file


class TestTiger:

    @pytest.fixture(autouse=True)
    def setup(self, temp_db_conn, placex_row, load_sql):
        load_sql('tables/search_name.sql', create_reverse_only=False)
        load_sql('tables/tiger.sql')

        # fake parent roads
        for x in range(-870, -863):
            for y in range(323, 328):
                placex_row(rank_search=26, rank_address=26,
                           geom=f"LINESTRING({x/10 - 0.1} {y/10}, {x/10 + 0.1} {y/10})")

        temp_db_conn.execute("""
            CREATE OR REPLACE FUNCTION get_partition(cc VARCHAR(10)) RETURNS INTEGER AS $$
              SELECT 0;
            $$ LANGUAGE sql;
            CREATE OR REPLACE FUNCTION token_matches_street(i JSONB, s INT[]) RETURNS BOOLEAN AS $$
             SELECT false
            $$ LANGUAGE SQL IMMUTABLE STRICT PARALLEL SAFE;
        """)

    @pytest.mark.parametrize("threads", (1, 5))
    @pytest.mark.asyncio
    async def test_add_tiger_data_database_frozen(self, def_config, src_dir, temp_db_cursor,
                                                  tokenizer_mock, threads):
        await tiger_data.add_tiger_data(str(src_dir / 'test' / 'testdb' / 'tiger'),
                                        def_config, threads, tokenizer_mock())

        assert temp_db_cursor.table_rows('location_property_tiger') == 6209

    @pytest.mark.asyncio
    async def test_add_tiger_data_reverse_only(self, def_config, src_dir, temp_db_cursor,
                                               tokenizer_mock):
        temp_db_cursor.execute("DROP TABLE search_name")

        with pytest.raises(UsageError,
                           match="Cannot perform tiger import: required tables are missing. "
                           "See https://github.com/osm-search/Nominatim/issues/2463 for details."):
            await tiger_data.add_tiger_data(str(src_dir / 'test' / 'testdb' / 'tiger'),
                                            def_config, 1, tokenizer_mock())

        assert temp_db_cursor.table_rows('location_property_tiger') == 0

    @pytest.mark.asyncio
    async def test_add_tiger_data_no_files(self, def_config, temp_db_cursor, tokenizer_mock,
                                           tmp_path):
        await tiger_data.add_tiger_data(str(tmp_path), def_config, 1, tokenizer_mock())

        assert temp_db_cursor.table_rows('location_property_tiger') == 0

    @pytest.mark.asyncio
    async def test_add_tiger_data_bad_file(self, def_config, temp_db_cursor, tokenizer_mock,
                                           tmp_path):
        sqlfile = tmp_path / '1010.csv'
        sqlfile.write_text('Random text', encoding='utf-8')

        await tiger_data.add_tiger_data(str(tmp_path), def_config, 1, tokenizer_mock())

        assert temp_db_cursor.table_rows('location_property_tiger') == 0

    @pytest.mark.asyncio
    async def test_add_tiger_data_hnr_nan(self, def_config, temp_db_cursor, tokenizer_mock,
                                          csv_factory, tmp_path):
        csv_factory('file1', hnr_to=99)
        csv_factory('file2', hnr_from='L12')
        csv_factory('file3', hnr_to='12.4')

        await tiger_data.add_tiger_data(str(tmp_path), def_config, 1, tokenizer_mock())

        rows = temp_db_cursor.row_set("""
            SELECT startnumber, endnumber FROM location_property_tiger""")

        assert rows == {(1, 99)}

    @pytest.mark.parametrize("threads", (1, 5))
    @pytest.mark.asyncio
    async def test_add_tiger_data_tarfile(self, def_config, temp_db_cursor, tokenizer_mock,
                                          tmp_path, src_dir, threads):
        tar = tarfile.open(str(tmp_path / 'sample.tar.gz'), "w:gz")
        tar.add(str(src_dir / 'test' / 'testdb' / 'tiger' / '01001.csv'))
        tar.close()

        await tiger_data.add_tiger_data(str(tmp_path / 'sample.tar.gz'), def_config, threads,
                                        tokenizer_mock())

        assert temp_db_cursor.table_rows('location_property_tiger') == 6209

    @pytest.mark.asyncio
    async def test_add_tiger_data_bad_tarfile(self, def_config, tokenizer_mock, tmp_path):
        tarfile = tmp_path / 'sample.tar.gz'
        tarfile.write_text("""Random text""", encoding='utf-8')

        with pytest.raises(UsageError):
            await tiger_data.add_tiger_data(str(tarfile), def_config, 1, tokenizer_mock())

    @pytest.mark.asyncio
    async def test_add_tiger_data_empty_tarfile(self, def_config, temp_db_cursor, tokenizer_mock,
                                                tmp_path):
        tar = tarfile.open(str(tmp_path / 'sample.tar.gz'), "w:gz")
        tar.add(__file__)
        tar.close()

        await tiger_data.add_tiger_data(str(tmp_path / 'sample.tar.gz'), def_config, 1,
                                        tokenizer_mock())

        assert temp_db_cursor.table_rows('location_property_tiger') == 0
