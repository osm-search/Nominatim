# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2026 by the Nominatim developer community.
# For a full list of authors see the git log.
import itertools
import sys
from pathlib import Path

import psycopg
from psycopg import sql as pysql
import pytest

# always test against the source
SRC_DIR = (Path(__file__) / '..' / '..' / '..').resolve()
sys.path.insert(0, str(SRC_DIR / 'src'))

from nominatim_db.config import Configuration
from nominatim_db.db import connection
from nominatim_db.db.sql_preprocessor import SQLPreprocessor
import nominatim_db.tokenizer.factory

import dummy_tokenizer
import mocks
from cursor import CursorForTesting


def _with_srid(geom, default=None):
    if geom is None:
        return None if default is None else f"SRID=4326;{default}"

    return f"SRID=4326;{geom}"


@pytest.fixture
def src_dir():
    return SRC_DIR


@pytest.fixture
def temp_db(monkeypatch):
    """ Create an empty database for the test. The database name is also
        exported into NOMINATIM_DATABASE_DSN.
    """
    name = 'test_nominatim_python_unittest'

    with psycopg.connect(dbname='postgres', autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(pysql.SQL('DROP DATABASE IF EXISTS') + pysql.Identifier(name))
            cur.execute(pysql.SQL('CREATE DATABASE') + pysql.Identifier(name))

    monkeypatch.setenv('NOMINATIM_DATABASE_DSN', 'dbname=' + name)

    with psycopg.connect(dbname=name) as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE EXTENSION hstore')

    yield name

    with psycopg.connect(dbname='postgres', autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute(pysql.SQL('DROP DATABASE IF EXISTS') + pysql.Identifier(name))


@pytest.fixture
def dsn(temp_db):
    return 'dbname=' + temp_db


@pytest.fixture
def temp_db_with_extensions(temp_db):
    with psycopg.connect(dbname=temp_db) as conn:
        with conn.cursor() as cur:
            cur.execute('CREATE EXTENSION postgis')

    return temp_db


@pytest.fixture
def temp_db_conn(temp_db):
    """ Connection to the test database.
    """
    with connection.connect('', autocommit=True, dbname=temp_db) as conn:
        connection.register_hstore(conn)
        yield conn


@pytest.fixture
def temp_db_cursor(temp_db):
    """ Connection and cursor towards the test database. The connection will
        be in auto-commit mode.
    """
    with psycopg.connect(dbname=temp_db, autocommit=True, cursor_factory=CursorForTesting) as conn:
        connection.register_hstore(conn)
        with conn.cursor() as cur:
            yield cur


@pytest.fixture
def table_factory(temp_db_conn):
    """ A fixture that creates new SQL tables, potentially filled with
        content.
    """
    def mk_table(name, definition='id INT', content=None):
        with psycopg.ClientCursor(temp_db_conn) as cur:
            cur.execute(pysql.SQL("CREATE TABLE {} ({})")
                             .format(pysql.Identifier(name),
                                     pysql.SQL(definition)))
            if content:
                sql = pysql.SQL("INSERT INTO {} VALUES ({})")\
                           .format(pysql.Identifier(name),
                                   pysql.SQL(',').join([pysql.Placeholder()
                                                        for _ in range(len(content[0]))]))
                cur.executemany(sql, content)

    return mk_table


@pytest.fixture
def def_config():
    cfg = Configuration(None)
    return cfg


@pytest.fixture
def project_env(tmp_path):
    projdir = tmp_path / 'project'
    projdir.mkdir()
    cfg = Configuration(projdir)
    return cfg


@pytest.fixture
def country_table(table_factory):
    table_factory('country_name', 'partition INT, country_code varchar(2), name hstore')


@pytest.fixture
def country_row(country_table, temp_db_cursor):
    def _add(partition=None, country=None, names=None):
        temp_db_cursor.insert_row('country_name', partition=partition,
                                  country_code=country, name=names)

    return _add


@pytest.fixture
def load_sql(temp_db_conn, country_row):
    proc = SQLPreprocessor(temp_db_conn, Configuration(None))

    def _run(filename, **kwargs):
        proc.run_sql_file(temp_db_conn, filename, **kwargs)

    return _run


@pytest.fixture
def property_table(load_sql, temp_db_conn):
    load_sql('tables/nominatim_properties.sql')

    return mocks.MockPropertyTable(temp_db_conn)


@pytest.fixture
def status_table(load_sql):
    """ Create an empty version of the status table and
        the status logging table.
    """
    load_sql('tables/status.sql')


@pytest.fixture
def place_table(temp_db_with_extensions, table_factory):
    """ Create an empty version of the place table.
    """
    table_factory('place',
                  """osm_id int8 NOT NULL,
                     osm_type char(1) NOT NULL,
                     class text NOT NULL,
                     type text NOT NULL,
                     name hstore,
                     admin_level smallint,
                     address hstore,
                     extratags hstore,
                     geometry Geometry(Geometry,4326) NOT NULL""")


@pytest.fixture
def place_row(place_table, temp_db_cursor):
    """ A factory for rows in the place table. The table is created as a
        prerequisite to the fixture.
    """
    idseq = itertools.count(1001)

    def _insert(osm_type='N', osm_id=None, cls='amenity', typ='cafe', names=None,
                admin_level=None, address=None, extratags=None, geom='POINT(0 0)'):
        args = {'osm_type': osm_type, 'osm_id': osm_id or next(idseq),
                'class': cls, 'type': typ, 'name': names, 'admin_level': admin_level,
                'address': address, 'extratags': extratags,
                'geometry': _with_srid(geom)}
        temp_db_cursor.insert_row('place', **args)

    return _insert


@pytest.fixture
def place_postcode_table(temp_db_with_extensions, table_factory):
    """ Create an empty version of the place_postcode table.
    """
    table_factory('place_postcode',
                  """osm_type char(1) NOT NULL,
                     osm_id bigint NOT NULL,
                     postcode text NOT NULL,
                     country_code text,
                     centroid Geometry(Point, 4326) NOT NULL,
                     geometry Geometry(Geometry, 4326)""")


@pytest.fixture
def place_postcode_row(place_postcode_table, temp_db_cursor):
    """ A factory for rows in the place_postcode table. The table is created as a
        prerequisite to the fixture.
    """
    idseq = itertools.count(5001)

    def _insert(osm_type='N', osm_id=None, postcode=None, country=None,
                centroid='POINT(12.0 4.0)', geom=None):
        temp_db_cursor.insert_row('place_postcode',
                                  osm_type=osm_type, osm_id=osm_id or next(idseq),
                                  postcode=postcode, country_code=country,
                                  centroid=_with_srid(centroid),
                                  geometry=_with_srid(geom))

    return _insert


@pytest.fixture
def placex_table(temp_db_with_extensions, temp_db_conn):
    """ Create an empty version of the place table.
    """
    return mocks.MockPlacexTable(temp_db_conn)


@pytest.fixture
def osmline_table(temp_db_with_extensions, load_sql):
    load_sql('tables/interpolation.sql')


@pytest.fixture
def sql_preprocessor_cfg(tmp_path, table_factory, temp_db_with_extensions, country_row):
    for part in range(3):
        country_row(partition=part)

    cfg = Configuration(None)
    cfg.set_libdirs(sql=tmp_path)
    return cfg


@pytest.fixture
def sql_preprocessor(sql_preprocessor_cfg, temp_db_conn):
    return SQLPreprocessor(temp_db_conn, sql_preprocessor_cfg)


@pytest.fixture
def tokenizer_mock(monkeypatch, property_table):
    """ Sets up the configuration so that the test dummy tokenizer will be
        loaded when the tokenizer factory is used. Also returns a factory
        with which a new dummy tokenizer may be created.
    """
    monkeypatch.setenv('NOMINATIM_TOKENIZER', 'dummy')

    def _import_dummy(*args, **kwargs):
        return dummy_tokenizer

    monkeypatch.setattr(nominatim_db.tokenizer.factory,
                        "_import_tokenizer", _import_dummy)
    property_table.set('tokenizer', 'dummy')

    def _create_tokenizer():
        return dummy_tokenizer.DummyTokenizer(None)

    return _create_tokenizer
