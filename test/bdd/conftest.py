# SPDX-License-Identifier: GPL-3.0-or-later
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2025 by the Nominatim developer community.
# For a full list of authors see the git log.
"""
Fixtures for BDD test steps
"""
import sys
import json
from pathlib import Path

import pytest
from pytest_bdd.parsers import re as step_parse
from pytest_bdd import when, then

from utils.api_runner import APIRunner
from utils.api_result import APIResult
from utils.checks import ResultAttr, COMPARATOR_TERMS

# always test against the source
SRC_DIR = (Path(__file__) / '..' / '..' / '..').resolve()
sys.path.insert(0, str(SRC_DIR / 'src'))


def _strlist(inp):
    return [s.strip() for s in inp.split(',')]


def _pretty_json(inp):
    return json.dumps(inp, indent=2)


def pytest_addoption(parser, pluginmanager):
    parser.addoption('--nominatim-purge', dest='NOMINATIM_PURGE', action='store_true',
                     help='Force recreation of test databases from scratch.')
    parser.addoption('--nominatim-keep-db', dest='NOMINATIM_KEEP_DB', action='store_true',
                     help='Do not drop the database after tests are finished.')
    parser.addoption('--nominatim-api-engine', dest='NOMINATIM_API_ENGINE',
                     default='falcon',
                     help='Chose the API engine to use when sending requests.')
    parser.addoption('--nominatim-tokenizer', dest='NOMINATIM_TOKENIZER',
                     metavar='TOKENIZER',
                     help='Use the specified tokenizer for importing data into '
                          'a Nominatim database.')

    parser.addini('nominatim_test_db', default='test_nominatim',
                  help='Name of the database used for running a single test.')
    parser.addini('nominatim_api_test_db', default='test_api_nominatim',
                  help='Name of the database for storing API test data.')
    parser.addini('nominatim_template_db', default='test_template_nominatim',
                  help='Name of database used as a template for test databases.')


@pytest.fixture
def datatable():
    """ Default fixture for datatables, so that their presence can be optional.
    """
    return None


@when(step_parse(r'reverse geocoding (?P<lat>[\d.-]*),(?P<lon>[\d.-]*)'),
      target_fixture='nominatim_result')
def reverse_geocode_via_api(test_config_env, pytestconfig, datatable, lat, lon):
    runner = APIRunner(test_config_env, pytestconfig.option.NOMINATIM_API_ENGINE)
    api_response = runner.run_step('reverse',
                                   {'lat': float(lat), 'lon': float(lon)},
                                   datatable, 'jsonv2', {})

    assert api_response.status == 200
    assert api_response.headers['content-type'] == 'application/json; charset=utf-8'

    result = APIResult('json', 'reverse', api_response.body)
    assert result.is_simple()

    return result


@when(step_parse(r'geocoding(?: "(?P<query>.*)")?'),
      target_fixture='nominatim_result')
def forward_geocode_via_api(test_config_env, pytestconfig, datatable, query):
    runner = APIRunner(test_config_env, pytestconfig.option.NOMINATIM_API_ENGINE)

    params = {'addressdetails': '1'}
    if query:
        params['q'] = query

    api_response = runner.run_step('search', params, datatable, 'jsonv2', {})

    assert api_response.status == 200
    assert api_response.headers['content-type'] == 'application/json; charset=utf-8'

    result = APIResult('json', 'search', api_response.body)
    assert not result.is_simple()

    return result


@then(step_parse(r'(?P<op>[a-z ]+) (?P<num>\d+) results? (?:are|is) returned'),
      converters={'num': int})
def check_number_of_results(nominatim_result, op, num):
    assert not nominatim_result.is_simple()
    assert COMPARATOR_TERMS[op](num, len(nominatim_result))


@then(step_parse('the result metadata contains'))
def check_metadata_for_fields(nominatim_result, datatable):
    if datatable[0] == ['param', 'value']:
        pairs = datatable[1:]
    else:
        pairs = zip(datatable[0], datatable[1])

    for k, v in pairs:
        assert ResultAttr(nominatim_result.meta, k) == v


@then(step_parse('the result metadata has no attributes (?P<attributes>.*)'),
      converters={'attributes': _strlist})
def check_metadata_for_field_presence(nominatim_result, attributes):
    assert all(a not in nominatim_result.meta for a in attributes), \
        f"Unexpectedly have one of the attributes '{attributes}' in\n" \
        f"{_pretty_json(nominatim_result.meta)}"


@then(step_parse(r'the result contains(?: in field (?P<field>\S+))?'))
def check_result_for_fields(nominatim_result, datatable, field):
    assert nominatim_result.is_simple()

    if datatable[0] == ['param', 'value']:
        pairs = datatable[1:]
    else:
        pairs = zip(datatable[0], datatable[1])

    prefix = field + '+' if field else ''

    for k, v in pairs:
        assert ResultAttr(nominatim_result.result, prefix + k) == v


@then(step_parse('the result has attributes (?P<attributes>.*)'),
      converters={'attributes': _strlist})
def check_result_for_field_presence(nominatim_result, attributes):
    assert nominatim_result.is_simple()
    assert all(a in nominatim_result.result for a in attributes)


@then(step_parse('the result has no attributes (?P<attributes>.*)'),
      converters={'attributes': _strlist})
def check_result_for_field_absence(nominatim_result, attributes):
    assert nominatim_result.is_simple()
    assert all(a not in nominatim_result.result for a in attributes)


@then(step_parse('the result set contains(?P<exact> exactly)?'))
def check_result_list_match(nominatim_result, datatable, exact):
    assert not nominatim_result.is_simple()

    result_set = set(range(len(nominatim_result.result)))

    for row in datatable[1:]:
        for idx in result_set:
            for key, value in zip(datatable[0], row):
                if ResultAttr(nominatim_result.result[idx], key) != value:
                    break
            else:
                # found a match
                result_set.remove(idx)
                break
        else:
            assert False, f"Missing data row {row}. Full response:\n{nominatim_result}"

    if exact:
        assert not [nominatim_result.result[i] for i in result_set]


@then(step_parse('all results have attributes (?P<attributes>.*)'),
      converters={'attributes': _strlist})
def check_all_results_for_field_presence(nominatim_result, attributes):
    assert not nominatim_result.is_simple()
    for res in nominatim_result.result:
        assert all(a in res for a in attributes), \
            f"Missing one of the attributes '{attributes}' in\n{_pretty_json(res)}"


@then(step_parse('all results have no attributes (?P<attributes>.*)'),
      converters={'attributes': _strlist})
def check_all_result_for_field_absence(nominatim_result, attributes):
    assert not nominatim_result.is_simple()
    for res in nominatim_result.result:
        assert all(a not in res for a in attributes), \
            f"Unexpectedly have one of the attributes '{attributes}' in\n{_pretty_json(res)}"


@then(step_parse(r'all results contain(?: in field (?P<field>\S+))?'))
def check_all_results_contain(nominatim_result, datatable, field):
    assert not nominatim_result.is_simple()

    if datatable[0] == ['param', 'value']:
        pairs = datatable[1:]
    else:
        pairs = zip(datatable[0], datatable[1])

    prefix = field + '+' if field else ''

    for k, v in pairs:
        for r in nominatim_result.result:
            assert ResultAttr(r, prefix + k) == v


@then(step_parse(r'result (?P<num>\d+) contains(?: in field (?P<field>\S+))?'),
      converters={'num': int})
def check_specific_result_for_fields(nominatim_result, datatable, num, field):
    assert not nominatim_result.is_simple()
    assert len(nominatim_result) >= num + 1

    if datatable[0] == ['param', 'value']:
        pairs = datatable[1:]
    else:
        pairs = zip(datatable[0], datatable[1])

    prefix = field + '+' if field else ''

    for k, v in pairs:
        assert ResultAttr(nominatim_result.result[num], prefix + k) == v
