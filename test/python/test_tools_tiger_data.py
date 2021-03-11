"""
Test for tiger data function
"""
from pathlib import Path

import pytest
import tarfile

from nominatim.tools import tiger_data, database_import


@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data(dsn, src_dir, def_config, tmp_path, sql_preprocessor,
                        temp_db_cursor, threads, temp_db):
    temp_db_cursor.execute('CREATE EXTENSION hstore')
    temp_db_cursor.execute('CREATE EXTENSION postgis')
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    sqlfile = tmp_path / '1010.sql'
    sqlfile.write_text("""INSERT INTO place values (1)""")
    tiger_data.add_tiger_data(dsn, str(tmp_path), threads, def_config, src_dir / 'lib-sql')

    assert temp_db_cursor.table_rows('place') == 1

@pytest.mark.parametrize("threads", (1, 5))
def test_add_tiger_data_tarfile(dsn, src_dir, def_config, tmp_path,
                        temp_db_cursor, threads, temp_db, sql_preprocessor):
    temp_db_cursor.execute('CREATE EXTENSION hstore')
    temp_db_cursor.execute('CREATE EXTENSION postgis')
    temp_db_cursor.execute('CREATE TABLE place (id INT)')
    sqlfile = tmp_path / '1010.sql'
    sqlfile.write_text("""INSERT INTO place values (1)""")
    tar = tarfile.open("sample.tar.gz", "w:gz")
    tar.add(sqlfile)
    tar.close()
    tiger_data.add_tiger_data(dsn, str(src_dir / 'sample.tar.gz'), threads, def_config, src_dir / 'lib-sql')
    
    assert temp_db_cursor.table_rows('place') == 1