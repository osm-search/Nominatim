# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Collector for all BDD API tests.

These tests work on a static test database that is the same for all tests.
The source data for the database can be found in the test/testdb directory.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest
from pytest_bdd.parsers import re as step_parse
from pytest_bdd import scenarios, when, given, then

from nominatim_db import cli
from nominatim_db.config import Configuration

from utils.db import DBManager
from utils.api_runner import APIRunner
from utils.api_result import APIResult


TESTDB_PATH = (Path(__file__) / '..' / '..' / 'testdb').resolve()

CONTENT_TYPES = {
    'json': 'application/json; charset=utf-8',
    'xml': 'text/xml; charset=utf-8',
    'geojson': 'application/json; charset=utf-8',
    'geocodejson': 'application/json; charset=utf-8',
    'html': 'text/html; charset=utf-8'
}


@pytest.fixture(autouse=True, scope='session')
def session_api_test_db(pytestconfig):
    """ Create a Nominatim database from the official API test data.
        Will only recreate an existing database if --nominatim-purge
        was set.
    """
    dbname = pytestconfig.getini('nominatim_api_test_db')

    config = Configuration(None).get_os_env()
    config['NOMINATIM_DATABASE_DSN'] = f"pgsql:dbname={dbname}"
    config['NOMINATIM_LANGUAGES'] = 'en,de,fr,ja'
    config['NOMINATIM_USE_US_TIGER_DATA'] = 'yes'
    if pytestconfig.option.NOMINATIM_TOKENIZER is not None:
        config['NOMINATIM_TOKENIZER'] = pytestconfig.option.NOMINATIM_TOKENIZER

    dbm = DBManager(purge=pytestconfig.option.NOMINATIM_PURGE)

    if not dbm.check_for_db(dbname):
        try:
            cli.nominatim(cli_args=['import', '--project-dir', str(TESTDB_PATH),
                                    '--osm-file', str(TESTDB_PATH / 'apidb-test-data.pbf')],
                          environ=config)
            cli.nominatim(cli_args=['add-data', '--project-dir', str(TESTDB_PATH),
                                    '--tiger-data', str(TESTDB_PATH / 'tiger')],
                          environ=config)
            cli.nominatim(cli_args=['freeze', '--project-dir', str(TESTDB_PATH)],
                          environ=config)
            cli.nominatim(cli_args=['special-phrases', '--project-dir', str(TESTDB_PATH),
                                    '--import-from-csv',
                                    str(TESTDB_PATH / 'full_en_phrases_test.csv')],
                          environ=config)
        except:  # noqa: E722
            dbm.drop_db(dbname)
            raise


@pytest.fixture
def test_config_env(pytestconfig):
    dbname = pytestconfig.getini('nominatim_api_test_db')

    config = Configuration(None).get_os_env()
    config['NOMINATIM_DATABASE_DSN'] = f"pgsql:dbname={dbname}"
    config['NOMINATIM_LANGUAGES'] = 'en,de,fr,ja'
    config['NOMINATIM_USE_US_TIGER_DATA'] = 'yes'
    if pytestconfig.option.NOMINATIM_TOKENIZER is not None:
        config['NOMINATIM_TOKENIZER'] = pytestconfig.option.NOMINATIM_TOKENIZER

    return config


@pytest.fixture
def api_http_request_headers():
    return {}


@given('the HTTP header', target_fixture='api_http_request_headers')
def set_additional_http_headers(api_http_request_headers, datatable):
    api_http_request_headers.update(zip(datatable[0], datatable[1]))
    return api_http_request_headers


@given('an unknown database', target_fixture='test_config_env')
def setup_connection_unknown_database(test_config_env):
    test_config_env['NOMINATIM_DATABASE_DSN'] = "pgsql:dbname=gerlkghngergn6732nf"
    return test_config_env


@when(step_parse(r'sending v1/(?P<endpoint>\S+)(?: with format (?P<fmt>\S+))?'),
      target_fixture='api_response')
def send_api_status(test_config_env, api_http_request_headers, pytestconfig,
                    datatable, endpoint, fmt):
    runner = APIRunner(test_config_env, pytestconfig.option.NOMINATIM_API_ENGINE)
    return runner.run_step(endpoint, {}, datatable, fmt, api_http_request_headers)


@then(step_parse(r'a HTTP (?P<status>\d+) is returned'), converters={'status': int})
def check_http_result(api_response, status):
    assert api_response.status == status


@then(step_parse('the page content equals "(?P<content>.*)"'))
def check_page_content_exact(api_response, content):
    assert api_response.body == content


@then('the result is valid html')
def check_for_html_correctness(api_response):
    assert api_response.headers['content-type'] == CONTENT_TYPES['html']

    try:
        tree = ET.fromstring(api_response.body)
    except Exception as ex:
        assert False, f"Could not parse page: {ex}\n{api_response.body}"

    assert tree.tag == 'html'

    body = tree.find('./body')
    assert body is not None
    assert body.find('.//script') is None


@then(step_parse(r'the result is valid (?P<fmt>\S+)(?: with (?P<num>\d+) results?)?'),
      target_fixture='nominatim_result')
def parse_api_json_response(api_response, fmt, num):
    assert api_response.headers['content-type'] == CONTENT_TYPES[fmt]

    result = APIResult(fmt, api_response.endpoint, api_response.body)

    if num:
        assert len(result) == int(num)

    return result


scenarios('features/api')
