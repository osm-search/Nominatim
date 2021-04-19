"""
Test for tiger data function
"""
from pathlib import Path

import pytest
import tarfile

from nominatim.tools import tiger_data, database_import


@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data(def_config, tmp_path, sql_preprocessor,
                        temp_db_cursor, threads, temp_db_with_extensions):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    sqlfile = tmp_path / '1010.sql'
    sqlfile.write_text("""INSERT INTO place values (1);
                          INSERT INTO non_existant_table values (1);""")
    tiger_data.add_tiger_data(str(tmp_path), def_config, threads)

    assert temp_db_cursor.table_rows('place') == 1


@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data_bad_file(def_config, tmp_path, sql_preprocessor,
                                 temp_db_cursor, threads, temp_db_with_extensions):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    sqlfile = tmp_path / '1010.txt'
    sqlfile.write_text("""Random text""")
    tiger_data.add_tiger_data(str(tmp_path), def_config, threads)

    assert temp_db_cursor.table_rows('place') == 0


@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data_tarfile(def_config, tmp_path, temp_db_cursor,
                                threads, temp_db_with_extensions, sql_preprocessor):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    sqlfile = tmp_path / '1010.sql'
    sqlfile.write_text("""INSERT INTO place values (1);
                          INSERT INTO non_existant_table values (1);""")
    tar = tarfile.open("sample.tar.gz", "w:gz")
    tar.add(sqlfile)
    tar.close()
    tiger_data.add_tiger_data(str(tmp_path), def_config, threads)

    assert temp_db_cursor.table_rows('place') == 1


@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data_bad_tarfile(def_config, tmp_path, temp_db_cursor, threads,
                                    temp_db_with_extensions, sql_preprocessor):
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    sqlfile = tmp_path / '1010.txt'
    sqlfile.write_text("""Random text""")
    tar = tarfile.open("sample.tar.gz", "w:gz")
    tar.add(sqlfile)
    tar.close()
    tiger_data.add_tiger_data(str(tmp_path), def_config, threads)

    assert temp_db_cursor.table_rows('place') == 0
