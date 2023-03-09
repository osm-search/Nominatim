# SPDX-License-Identifier: GPL-2.0-only
#
# This file is part of Nominatim. (https://nominatim.org)
#
# Copyright (C) 2022 by the Nominatim developer community.
# For a full list of authors see the git log.
""" Steps that run queries against the API.

    Queries may either be run directly via PHP using the query script
    or via the HTTP interface using php-cgi.
"""
from pathlib import Path
import json
import os
import re
import logging
import asyncio
from urllib.parse import urlencode

from utils import run_script
from http_responses import GenericResponse, SearchResponse, ReverseResponse, StatusResponse
from check_functions import Bbox, check_for_attributes
from table_compare import NominatimID

LOG = logging.getLogger(__name__)

BASE_SERVER_ENV = {
    'HTTP_HOST' : 'localhost',
    'HTTP_USER_AGENT' : 'Mozilla/5.0 (X11; Linux x86_64; rv:51.0) Gecko/20100101 Firefox/51.0',
    'HTTP_ACCEPT' : 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'HTTP_ACCEPT_ENCODING' : 'gzip, deflate',
    'HTTP_CONNECTION' : 'keep-alive',
    'SERVER_SIGNATURE' : '<address>Nominatim BDD Tests</address>',
    'SERVER_SOFTWARE' : 'Nominatim test',
    'SERVER_NAME' : 'localhost',
    'SERVER_ADDR' : '127.0.1.1',
    'SERVER_PORT' : '80',
    'REMOTE_ADDR' : '127.0.0.1',
    'DOCUMENT_ROOT' : '/var/www',
    'REQUEST_SCHEME' : 'http',
    'CONTEXT_PREFIX' : '/',
    'SERVER_ADMIN' : 'webmaster@localhost',
    'REMOTE_PORT' : '49319',
    'GATEWAY_INTERFACE' : 'CGI/1.1',
    'SERVER_PROTOCOL' : 'HTTP/1.1',
    'REQUEST_METHOD' : 'GET',
    'REDIRECT_STATUS' : 'CGI'
}


def make_todo_list(context, result_id):
    if result_id is None:
        context.execute_steps("then at least 1 result is returned")
        return range(len(context.response.result))

    context.execute_steps(f"then more than {result_id}results are returned")
    return (int(result_id.strip()), )


def compare(operator, op1, op2):
    if operator == 'less than':
        return op1 < op2
    elif operator == 'more than':
        return op1 > op2
    elif operator == 'exactly':
        return op1 == op2
    elif operator == 'at least':
        return op1 >= op2
    elif operator == 'at most':
        return op1 <= op2
    else:
        raise Exception("unknown operator '%s'" % operator)


def send_api_query(endpoint, params, fmt, context):
    if fmt is not None and fmt.strip() != 'debug':
        params['format'] = fmt.strip()
    if context.table:
        if context.table.headings[0] == 'param':
            for line in context.table:
                params[line['param']] = line['value']
        else:
            for h in context.table.headings:
                params[h] = context.table[0][h]

    if context.nominatim.api_engine is None:
        return send_api_query_php(endpoint, params, context)

    return asyncio.run(context.nominatim.api_engine(endpoint, params,
                                                    Path(context.nominatim.website_dir.name),
                                                    context.nominatim.test_env,
                                                    getattr(context, 'http_headers', {})))



def send_api_query_php(endpoint, params, context):
    env = dict(BASE_SERVER_ENV)
    env['QUERY_STRING'] = urlencode(params)

    env['SCRIPT_NAME'] = '/%s.php' % endpoint
    env['REQUEST_URI'] = '%s?%s' % (env['SCRIPT_NAME'], env['QUERY_STRING'])
    env['CONTEXT_DOCUMENT_ROOT'] = os.path.join(context.nominatim.website_dir.name, 'website')
    env['SCRIPT_FILENAME'] = os.path.join(env['CONTEXT_DOCUMENT_ROOT'],
                                          '%s.php' % endpoint)

    LOG.debug("Environment:" + json.dumps(env, sort_keys=True, indent=2))

    if hasattr(context, 'http_headers'):
        env.update(context.http_headers)

    cmd = ['/usr/bin/env', 'php-cgi', '-f']
    if context.nominatim.code_coverage_path:
        env['XDEBUG_MODE'] = 'coverage'
        env['COV_SCRIPT_FILENAME'] = env['SCRIPT_FILENAME']
        env['COV_PHP_DIR'] = context.nominatim.src_dir
        env['COV_TEST_NAME'] = '%s:%s' % (context.scenario.filename, context.scenario.line)
        env['SCRIPT_FILENAME'] = \
                os.path.join(os.path.split(__file__)[0], 'cgi-with-coverage.php')
        cmd.append(env['SCRIPT_FILENAME'])
        env['PHP_CODE_COVERAGE_FILE'] = context.nominatim.next_code_coverage_file()
    else:
        cmd.append(env['SCRIPT_FILENAME'])

    for k,v in params.items():
        cmd.append("%s=%s" % (k, v))

    outp, err = run_script(cmd, cwd=context.nominatim.website_dir.name, env=env)

    assert len(err) == 0, "Unexpected PHP error: %s" % (err)

    if outp.startswith('Status: '):
        status = int(outp[8:11])
    else:
        status = 200

    content_start = outp.find('\r\n\r\n')

    return outp[content_start + 4:], status

@given(u'the HTTP header')
def add_http_header(context):
    if not hasattr(context, 'http_headers'):
        context.http_headers = {}

    for h in context.table.headings:
        envvar = 'HTTP_' + h.upper().replace('-', '_')
        context.http_headers[envvar] = context.table[0][h]


@when(u'sending (?P<fmt>\S+ )?search query "(?P<query>.*)"(?P<addr> with address)?')
def website_search_request(context, fmt, query, addr):
    params = {}
    if query:
        params['q'] = query
    if addr is not None:
        params['addressdetails'] = '1'
    if fmt and fmt.strip() == 'debug':
        params['debug'] = '1'

    outp, status = send_api_query('search', params, fmt, context)

    context.response = SearchResponse(outp, fmt or 'json', status)

@when(u'sending (?P<fmt>\S+ )?reverse coordinates (?P<lat>.+)?,(?P<lon>.+)?')
def website_reverse_request(context, fmt, lat, lon):
    params = {}
    if lat is not None:
        params['lat'] = lat
    if lon is not None:
        params['lon'] = lon
    if fmt and fmt.strip() == 'debug':
        params['debug'] = '1'

    outp, status = send_api_query('reverse', params, fmt, context)

    context.response = ReverseResponse(outp, fmt or 'xml', status)

@when(u'sending (?P<fmt>\S+ )?reverse point (?P<nodeid>.+)')
def website_reverse_request(context, fmt, nodeid):
    params = {}
    if fmt and fmt.strip() == 'debug':
        params['debug'] = '1'
    params['lon'], params['lat'] = (f'{c:f}' for c in context.osm.grid_node(int(nodeid)))


    outp, status = send_api_query('reverse', params, fmt, context)

    context.response = ReverseResponse(outp, fmt or 'xml', status)



@when(u'sending (?P<fmt>\S+ )?details query for (?P<query>.*)')
def website_details_request(context, fmt, query):
    params = {}
    if query[0] in 'NWR':
        nid = NominatimID(query)
        params['osmtype'] = nid.typ
        params['osmid'] = nid.oid
        if nid.cls:
            params['class'] = nid.cls
    else:
        params['place_id'] = query
    outp, status = send_api_query('details', params, fmt, context)

    context.response = GenericResponse(outp, fmt or 'json', status)

@when(u'sending (?P<fmt>\S+ )?lookup query for (?P<query>.*)')
def website_lookup_request(context, fmt, query):
    params = { 'osm_ids' : query }
    outp, status = send_api_query('lookup', params, fmt, context)

    context.response = SearchResponse(outp, fmt or 'xml', status)

@when(u'sending (?P<fmt>\S+ )?status query')
def website_status_request(context, fmt):
    params = {}
    outp, status = send_api_query('status', params, fmt, context)

    context.response = StatusResponse(outp, fmt or 'text', status)

@step(u'(?P<operator>less than|more than|exactly|at least|at most) (?P<number>\d+) results? (?:is|are) returned')
def validate_result_number(context, operator, number):
    assert context.response.errorcode == 200
    numres = len(context.response.result)
    assert compare(operator, numres, int(number)), \
        "Bad number of results: expected {} {}, got {}.".format(operator, number, numres)

@then(u'a HTTP (?P<status>\d+) is returned')
def check_http_return_status(context, status):
    assert context.response.errorcode == int(status), \
           "Return HTTP status is {}.".format(context.response.errorcode)

@then(u'the page contents equals "(?P<text>.+)"')
def check_page_content_equals(context, text):
    assert context.response.page == text

@then(u'the result is valid (?P<fmt>\w+)')
def step_impl(context, fmt):
    context.execute_steps("Then a HTTP 200 is returned")
    assert context.response.format == fmt

@then(u'a (?P<fmt>\w+) user error is returned')
def check_page_error(context, fmt):
    context.execute_steps("Then a HTTP 400 is returned")
    assert context.response.format == fmt

    if fmt == 'xml':
        assert re.search(r'<error>.+</error>', context.response.page, re.DOTALL) is not None
    else:
        assert re.search(r'({"error":)', context.response.page, re.DOTALL) is not None

@then(u'result header contains')
def check_header_attr(context):
    for line in context.table:
        assert re.fullmatch(line['value'], context.response.header[line['attr']]) is not None, \
               "attribute '%s': expected: '%s', got '%s'" % (
                    line['attr'], line['value'],
                    context.response.header[line['attr']])


@then(u'result header has (?P<neg>not )?attributes (?P<attrs>.*)')
def check_header_no_attr(context, neg, attrs):
    check_for_attributes(context.response.header, attrs,
                         'absent' if neg else 'present')


@then(u'results contain')
def step_impl(context):
    context.execute_steps("then at least 1 result is returned")

    for line in context.table:
        context.response.match_row(line, context=context)


@then(u'result (?P<lid>\d+ )?has (?P<neg>not )?attributes (?P<attrs>.*)')
def validate_attributes(context, lid, neg, attrs):
    for i in make_todo_list(context, lid):
        check_for_attributes(context.response.result[i], attrs,
                             'absent' if neg else 'present')


@then(u'result addresses contain')
def step_impl(context):
    context.execute_steps("then at least 1 result is returned")

    for line in context.table:
        idx = int(line['ID']) if 'ID' in line.headings else None

        for name, value in zip(line.headings, line.cells):
            if name != 'ID':
                context.response.assert_address_field(idx, name, value)

@then(u'address of result (?P<lid>\d+) has(?P<neg> no)? types (?P<attrs>.*)')
def check_address(context, lid, neg, attrs):
    context.execute_steps("then more than %s results are returned" % lid)

    addr_parts = context.response.result[int(lid)]['address']

    for attr in attrs.split(','):
        if neg:
            assert attr not in addr_parts
        else:
            assert attr in addr_parts

@then(u'address of result (?P<lid>\d+) (?P<complete>is|contains)')
def check_address(context, lid, complete):
    context.execute_steps("then more than %s results are returned" % lid)

    lid = int(lid)
    addr_parts = dict(context.response.result[lid]['address'])

    for line in context.table:
        context.response.assert_address_field(lid, line['type'], line['value'])
        del addr_parts[line['type']]

    if complete == 'is':
        assert len(addr_parts) == 0, "Additional address parts found: %s" % str(addr_parts)


@then(u'result (?P<lid>\d+ )?has bounding box in (?P<coords>[\d,.-]+)')
def check_bounding_box_in_area(context, lid, coords):
    expected = Bbox(coords)

    for idx in make_todo_list(context, lid):
        res = context.response.result[idx]
        check_for_attributes(res, 'boundingbox')
        context.response.check_row(idx, res['boundingbox'] in expected,
                                   f"Bbox is not contained in {expected}")


@then(u'result (?P<lid>\d+ )?has centroid in (?P<coords>[\d,.-]+)')
def check_centroid_in_area(context, lid, coords):
    expected = Bbox(coords)

    for idx in make_todo_list(context, lid):
        res = context.response.result[idx]
        check_for_attributes(res, 'lat,lon')
        context.response.check_row(idx, (res['lon'], res['lat']) in expected,
                                   f"Centroid is not inside {expected}")


@then(u'there are(?P<neg> no)? duplicates')
def check_for_duplicates(context, neg):
    context.execute_steps("then at least 1 result is returned")

    resarr = set()
    has_dupe = False

    for res in context.response.result:
        dup = (res['osm_type'], res['class'], res['type'], res['display_name'])
        if dup in resarr:
            has_dupe = True
            break
        resarr.add(dup)

    if neg:
        assert not has_dupe, "Found duplicate for %s" % (dup, )
    else:
        assert has_dupe, "No duplicates found"

