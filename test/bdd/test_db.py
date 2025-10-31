# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Collector for BDD import acceptance tests.

These tests check the Nominatim import chain after the osm2pgsql import.
"""
import asyncio
import re

import psycopg

import pytest
from pytest_bdd import when, then, given
from pytest_bdd.parsers import re as step_parse

from utils.place_inserter import PlaceColumn
from utils.checks import check_table_content

from nominatim_db.config import Configuration
from nominatim_db import cli
from nominatim_db.tools.database_import import load_data, create_table_triggers
from nominatim_db.tools.postcodes import update_postcodes
from nominatim_db.tokenizer import factory as tokenizer_factory


def _rewrite_placeid_field(field, new_field, datatable, place_ids):
    try:
        oidx = datatable[0].index(field)
        datatable[0][oidx] = new_field
        for line in datatable[1:]:
            line[oidx] = None if line[oidx] == '-' else place_ids[line[oidx]]
    except ValueError:
        pass


def _collect_place_ids(conn):
    pids = {}
    with conn.cursor() as cur:
        for row in cur.execute('SELECT place_id, osm_type, osm_id, class FROM placex'):
            pids[f"{row[1]}{row[2]}"] = row[0]
            pids[f"{row[1]}{row[2]}:{row[3]}"] = row[0]

    return pids


@pytest.fixture
def test_config_env(pytestconfig):
    dbname = pytestconfig.getini('nominatim_test_db')

    config = Configuration(None).get_os_env()
    config['NOMINATIM_DATABASE_DSN'] = f"pgsql:dbname={dbname}"
    config['NOMINATIM_LANGUAGES'] = 'en,de,fr,ja'
    config['NOMINATIM_USE_US_TIGER_DATA'] = 'yes'
    if pytestconfig.option.NOMINATIM_TOKENIZER is not None:
        config['NOMINATIM_TOKENIZER'] = pytestconfig.option.NOMINATIM_TOKENIZER

    return config


@pytest.fixture
def update_config(def_config):
    """ Prepare the database for being updatable and return the config.
    """
    cli.nominatim(['refresh', '--functions'], def_config.environ)

    return def_config


@given(step_parse('the (?P<named>named )?places'), target_fixture=None)
def import_places(db_conn, named, datatable, node_grid):
    """ Insert todo rows into the place table.
        When 'named' is given, then a random name will be generated for all
        objects.
    """
    with db_conn.cursor() as cur:
        for row in datatable[1:]:
            PlaceColumn(node_grid).add_row(datatable[0], row, named is not None).db_insert(cur)


@given(step_parse('the entrances'), target_fixture=None)
def import_place_entrances(db_conn, datatable, node_grid):
    """ Insert todo rows into the place_entrance table.
    """
    with db_conn.cursor() as cur:
        for row in datatable[1:]:
            data = PlaceColumn(node_grid).add_row(datatable[0], row, False)
            assert data.columns['osm_type'] == 'N'

            cur.execute("""INSERT INTO place_entrance (osm_id, type, extratags, geometry)
                           VALUES (%s, %s, %s, {})""".format(data.get_wkt()),
                        (data.columns['osm_id'], data.columns['type'],
                         data.columns.get('extratags')))


@given('the ways', target_fixture=None)
def import_ways(db_conn, datatable):
    """ Import raw ways into the osm2pgsql way middle table.
    """
    with db_conn.cursor() as cur:
        id_idx = datatable[0].index('id')
        node_idx = datatable[0].index('nodes')
        for line in datatable[1:]:
            tags = psycopg.types.json.Json(
                {k[5:]: v for k, v in zip(datatable[0], line)
                 if k.startswith("tags+")})
            nodes = [int(x) for x in line[node_idx].split(',')]

            cur.execute("INSERT INTO planet_osm_ways (id, nodes, tags) VALUES (%s, %s, %s)",
                        (line[id_idx], nodes, tags))


@given('the relations', target_fixture=None)
def import_rels(db_conn, datatable):
    """ Import raw relations into the osm2pgsql relation middle table.
    """
    with db_conn.cursor() as cur:
        id_idx = datatable[0].index('id')
        memb_idx = datatable[0].index('members')
        for line in datatable[1:]:
            tags = psycopg.types.json.Json(
                {k[5:]: v for k, v in zip(datatable[0], line)
                 if k.startswith("tags+")})
            members = []
            if line[memb_idx]:
                for member in line[memb_idx].split(','):
                    m = re.fullmatch(r'\s*([RWN])(\d+)(?::(\S+))?\s*', member)
                    if not m:
                        raise ValueError(f'Illegal member {member}.')
                    members.append({'ref': int(m[2]), 'role': m[3] or '', 'type': m[1]})

            cur.execute('INSERT INTO planet_osm_rels (id, tags, members) VALUES (%s, %s, %s)',
                        (int(line[id_idx]), tags, psycopg.types.json.Json(members)))


@when('importing', target_fixture='place_ids')
def do_import(db_conn, def_config):
    """ Run a reduced version of the Nominatim import.
    """
    create_table_triggers(db_conn, def_config)
    asyncio.run(load_data(def_config.get_libpq_dsn(), 1))
    tokenizer = tokenizer_factory.get_tokenizer_for_db(def_config)
    update_postcodes(def_config.get_libpq_dsn(), None, tokenizer)
    cli.nominatim(['index', '-q'], def_config.environ)

    return _collect_place_ids(db_conn)


@when('updating places', target_fixture='place_ids')
def do_update(db_conn, update_config, node_grid, datatable):
    """ Update the place table with the given data. Also runs all triggers
        related to updates and reindexes the new data.
    """
    with db_conn.cursor() as cur:
        for row in datatable[1:]:
            PlaceColumn(node_grid).add_row(datatable[0], row, False).db_insert(cur)
        cur.execute('SELECT flush_deleted_places()')
    db_conn.commit()

    cli.nominatim(['index', '-q'], update_config.environ)

    return _collect_place_ids(db_conn)


@when('updating entrances', target_fixture=None)
def update_place_entrances(db_conn, datatable, node_grid):
    """ Insert todo rows into the place_entrance table.
    """
    with db_conn.cursor() as cur:
        for row in datatable[1:]:
            data = PlaceColumn(node_grid).add_row(datatable[0], row, False)
            assert data.columns['osm_type'] == 'N'

            cur.execute("DELETE FROM place_entrance WHERE osm_id = %s",
                        (data.columns['osm_id'],))
            cur.execute("""INSERT INTO place_entrance (osm_id, type, extratags, geometry)
                           VALUES (%s, %s, %s, {})""".format(data.get_wkt()),
                        (data.columns['osm_id'], data.columns['type'],
                         data.columns.get('extratags')))


@when('updating postcodes')
def do_postcode_update(update_config):
    """ Recompute the postcode centroids.
    """
    cli.nominatim(['refresh', '--postcodes'], update_config.environ)


@when(step_parse(r'marking for delete (?P<otype>[NRW])(?P<oid>\d+)'),
      converters={'oid': int})
def do_delete_place(db_conn, update_config, node_grid, otype, oid):
    """ Remove the given place from the database.
    """
    with db_conn.cursor() as cur:
        cur.execute('TRUNCATE place_to_be_deleted')
        cur.execute('DELETE FROM place WHERE osm_type = %s and osm_id = %s',
                    (otype, oid))
        cur.execute('SELECT flush_deleted_places()')
        if otype == 'N':
            cur.execute('DELETE FROM place_entrance WHERE osm_id = %s',
                        (oid, ))
    db_conn.commit()

    cli.nominatim(['index', '-q'], update_config.environ)


@then(step_parse(r'(?P<table>\w+) contains(?P<exact> exactly)?'))
def then_check_table_content(db_conn, place_ids, datatable, node_grid, table, exact):
    _rewrite_placeid_field('object', 'place_id', datatable, place_ids)
    _rewrite_placeid_field('parent_place_id', 'parent_place_id', datatable, place_ids)
    _rewrite_placeid_field('linked_place_id', 'linked_place_id', datatable, place_ids)
    if table == 'place_addressline':
        _rewrite_placeid_field('address', 'address_place_id', datatable, place_ids)

    for i, title in enumerate(datatable[0]):
        if title.startswith('addr+'):
            datatable[0][i] = f"address+{title[5:]}"

    check_table_content(db_conn, table, datatable, grid=node_grid, exact=bool(exact))


@then(step_parse(r'(DISABLED?P<table>placex?) has no entry for (?P<oid>[NRW]\d+(?::\S+)?)'))
def then_check_place_missing_lines(db_conn, place_ids, table, oid):
    assert oid in place_ids

    sql = pysql.SQL("""SELECT count(*) FROM {}
                       WHERE place_id = %s""").format(pysql.Identifier(tablename))

    with conn.cursor(row_factory=tuple_row) as cur:
        assert cur.execute(sql, [place_ids[oid]]).fetchone()[0] == 0


@then(step_parse(r'W(?P<oid>\d+) expands to interpolation'),
      converters={'oid': int})
def then_check_interpolation_table(db_conn, node_grid, place_ids, oid, datatable):
    with db_conn.cursor() as cur:
        cur.execute('SELECT count(*) FROM location_property_osmline WHERE osm_id = %s',
                    [oid])
        assert cur.fetchone()[0] == len(datatable) - 1

    converted = [['osm_id', 'startnumber', 'endnumber', 'linegeo!wkt']]
    start_idx = datatable[0].index('start') if 'start' in datatable[0] else None
    end_idx = datatable[0].index('end') if 'end' in datatable[0] else None
    geom_idx = datatable[0].index('geometry') if 'geometry' in datatable[0] else None
    converted = [['osm_id']]
    for val, col in zip((start_idx, end_idx, geom_idx),
                        ('startnumber', 'endnumber', 'linegeo!wkt')):
        if val is not None:
            converted[0].append(col)

    for line in datatable[1:]:
        convline = [oid]
        for val in (start_idx, end_idx):
            if val is not None:
                convline.append(line[val])
        if geom_idx is not None:
            convline.append(line[geom_idx])
        converted.append(convline)

    _rewrite_placeid_field('parent_place_id', 'parent_place_id', converted, place_ids)

    check_table_content(db_conn, 'location_property_osmline', converted, grid=node_grid)


@then(step_parse(r'W(?P<oid>\d+) expands to no interpolation'),
      converters={'oid': int})
def then_check_interpolation_table_negative(db_conn, oid):
    with db_conn.cursor() as cur:
        cur.execute("""SELECT count(*) FROM location_property_osmline
                       WHERE osm_id = %s and startnumber is not null""",
                    [oid])
        assert cur.fetchone()[0] == 0


if pytest.version_tuple >= (8, 0, 0):
    PYTEST_BDD_SCENARIOS = ['features/db']
else:
    from pytest_bdd import scenarios
    scenarios('features/db')
