# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Test for tiger data function
"""
import tarfile
from textwrap import dedent

import pytest

from nominatim.tools import tiger_data
from nominatim.errors import UsageError

class MockTigerTable:

    def __init__(self, conn):
        self.conn = conn
        with conn.cursor() as cur:
            cur.execute("""CREATE TABLE tiger (linegeo GEOMETRY,
                                               start INTEGER,
                                               stop INTEGER,
                                               interpol TEXT,
                                               token_info JSONB,
                                               postcode TEXT)""")

    def count(self):
        with self.conn.cursor() as cur:
            return cur.scalar("SELECT count(*) FROM tiger")

    def row(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT * FROM tiger LIMIT 1")
            return cur.fetchone()

@pytest.fixture
def tiger_table(def_config, temp_db_conn, sql_preprocessor,
                temp_db_with_extensions, tmp_path):
    def_config.lib_dir.sql = tmp_path / 'sql'
    def_config.lib_dir.sql.mkdir()

    (def_config.lib_dir.sql / 'tiger_import_start.sql').write_text(
        """CREATE OR REPLACE FUNCTION tiger_line_import(linegeo GEOMETRY, start INTEGER,
                                                        stop INTEGER, interpol TEXT,
                                                        token_info JSONB, postcode TEXT)
           RETURNS INTEGER AS $$
            INSERT INTO tiger VALUES(linegeo, start, stop, interpol, token_info, postcode)
            RETURNING 1
           $$ LANGUAGE SQL;""")
    (def_config.lib_dir.sql / 'tiger_import_finish.sql').write_text(
        """DROP FUNCTION tiger_line_import (linegeo GEOMETRY, in_startnumber INTEGER,
                                 in_endnumber INTEGER, interpolationtype TEXT,
                                 token_info JSONB, in_postcode TEXT);""")

    return MockTigerTable(temp_db_conn)


@pytest.fixture
def csv_factory(tmp_path):
    def _mk_file(fname, hnr_from=1, hnr_to=9, interpol='odd', street='Main St',
                 city='Newtown', state='AL', postcode='12345',
                 geometry='LINESTRING(-86.466995 32.428956,-86.466923 32.428933)'):
        (tmp_path / (fname + '.csv')).write_text(dedent("""\
        from;to;interpolation;street;city;state;postcode;geometry
        {};{};{};{};{};{};{};{}
        """.format(hnr_from, hnr_to, interpol, street, city, state,
                   postcode, geometry)))

    return _mk_file


@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data(def_config, src_dir, tiger_table, tokenizer_mock, threads):
    tiger_data.add_tiger_data(str(src_dir / 'test' / 'testdb' / 'tiger'),
                              def_config, threads, tokenizer_mock())

    assert tiger_table.count() == 6213


def test_add_tiger_data_no_files(def_config, tiger_table, tokenizer_mock,
                                 tmp_path):
    tiger_data.add_tiger_data(str(tmp_path), def_config, 1, tokenizer_mock())

    assert tiger_table.count() == 0


def test_add_tiger_data_bad_file(def_config, tiger_table, tokenizer_mock,
                                 tmp_path):
    sqlfile = tmp_path / '1010.csv'
    sqlfile.write_text("""Random text""")

    tiger_data.add_tiger_data(str(tmp_path), def_config, 1, tokenizer_mock())

    assert tiger_table.count() == 0


def test_add_tiger_data_hnr_nan(def_config, tiger_table, tokenizer_mock,
                                csv_factory, tmp_path):
    csv_factory('file1', hnr_from=99)
    csv_factory('file2', hnr_from='L12')
    csv_factory('file3', hnr_to='12.4')

    tiger_data.add_tiger_data(str(tmp_path), def_config, 1, tokenizer_mock())

    assert tiger_table.count() == 1
    assert tiger_table.row()['start'] == 99


@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data_tarfile(def_config, tiger_table, tokenizer_mock,
                                tmp_path, src_dir, threads):
    tar = tarfile.open(str(tmp_path / 'sample.tar.gz'), "w:gz")
    tar.add(str(src_dir / 'test' / 'testdb' / 'tiger' / '01001.csv'))
    tar.close()

    tiger_data.add_tiger_data(str(tmp_path / 'sample.tar.gz'), def_config, threads,
                              tokenizer_mock())

    assert tiger_table.count() == 6213


def test_add_tiger_data_bad_tarfile(def_config, tiger_table, tokenizer_mock,
                                    tmp_path):
    tarfile = tmp_path / 'sample.tar.gz'
    tarfile.write_text("""Random text""")

    with pytest.raises(UsageError):
        tiger_data.add_tiger_data(str(tarfile), def_config, 1, tokenizer_mock())


def test_add_tiger_data_empty_tarfile(def_config, tiger_table, tokenizer_mock,
                                      tmp_path):
    tar = tarfile.open(str(tmp_path / 'sample.tar.gz'), "w:gz")
    tar.add(__file__)
    tar.close()

    tiger_data.add_tiger_data(str(tmp_path / 'sample.tar.gz'), def_config, 1,
                              tokenizer_mock())

    assert tiger_table.count() == 0
