import sys
from pathlib import Path

import psycopg2
import pytest

# always test against the source
sys.path.insert(0, str((Path(__file__) / '..' / '..' / '..').resolve()))

@pytest.fixture
def temp_db(monkeypatch):
    name = 'test_nominatim_python_unittest'
    with psycopg2.connect(database='postgres') as conn:
        conn.set_isolation_level(0)
        with conn.cursor() as cur:
            cur.execute('DROP DATABASE IF EXISTS {}'.format(name))
            cur.execute('CREATE DATABASE {}'.format(name))

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN' , 'dbname=' + name)

    yield name

    with psycopg2.connect(database='postgres') as conn:
        conn.set_isolation_level(0)
        with conn.cursor() as cur:
            cur.execute('DROP DATABASE IF EXISTS {}'.format(name))
