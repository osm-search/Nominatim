""" Steps that run queries against the API.

    Queries may either be run directly via PHP using the query script
    or via the HTTP interface using php-cgi.
"""
import json
import os
import re
import logging
from urllib.parse import urlencode

from utils import run_script
from http_responses import GenericResponse, SearchResponse, ReverseResponse, StatusResponse

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


@when(u'searching for "(?P<query>.*)"(?P<dups> with dups)?')
def query_cmd(context, query, dups):
    """ Query directly via PHP script.
    """
    cmd = ['/usr/bin/env', 'php']
    cmd.append(os.path.join(context.nominatim.build_dir, 'utils', 'query.php'))
    if query:
        cmd.extend(['--search', query])
    # add more parameters in table form
    if context.table:
        for h in context.table.headings:
            value = context.table[0][h].strip()
            if value:
                cmd.extend(('--' + h, value))

    if dups:
        cmd.extend(('--dedupe', '0'))

    outp, err = run_script(cmd, cwd=context.nominatim.build_dir)

    context.response = SearchResponse(outp, 'json')

def send_api_query(endpoint, params, fmt, context):
    if fmt is not None:
        params['format'] = fmt.strip()
    if context.table:
        if context.table.headings[0] == 'param':
            for line in context.table:
                params[line['param']] = line['value']
        else:
            for h in context.table.headings:
                params[h] = context.table[0][h]

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
        env['COV_SCRIPT_FILENAME'] = env['SCRIPT_FILENAME']
        env['COV_PHP_DIR'] = os.path.join(context.nominatim.src_dir, "lib")
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

    outp, status = send_api_query('search', params, fmt, context)

    context.response = SearchResponse(outp, fmt or 'json', status)

@when(u'sending (?P<fmt>\S+ )?reverse coordinates (?P<lat>.+)?,(?P<lon>.+)?')
def website_reverse_request(context, fmt, lat, lon):
    params = {}
    if lat is not None:
        params['lat'] = lat
    if lon is not None:
        params['lon'] = lon

    outp, status = send_api_query('reverse', params, fmt, context)

    context.response = ReverseResponse(outp, fmt or 'xml', status)

@when(u'sending (?P<fmt>\S+ )?details query for (?P<query>.*)')
def website_details_request(context, fmt, query):
    params = {}
    if query[0] in 'NWR':
        params['osmtype'] = query[0]
        params['osmid'] = query[1:]
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
        "Bad number of results: expected %s %s, got %d." % (operator, number, numres)

@then(u'a HTTP (?P<status>\d+) is returned')
def check_http_return_status(context, status):
    assert context.response.errorcode == int(status)

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
    for attr in attrs.split(','):
        if neg:
            assert attr not in context.response.header
        else:
            assert attr in context.response.header

@then(u'results contain')
def step_impl(context):
    context.execute_steps("then at least 1 result is returned")

    for line in context.table:
        context.response.match_row(line)

@then(u'result (?P<lid>\d+ )?has (?P<neg>not )?attributes (?P<attrs>.*)')
def validate_attributes(context, lid, neg, attrs):
    if lid is None:
        idx = range(len(context.response.result))
        context.execute_steps("then at least 1 result is returned")
    else:
        idx = [int(lid.strip())]
        context.execute_steps("then more than %sresults are returned" % lid)

    for i in idx:
        for attr in attrs.split(','):
            if neg:
                assert attr not in context.response.result[i]
            else:
                assert attr in context.response.result[i]

@then(u'result addresses contain')
def step_impl(context):
    context.execute_steps("then at least 1 result is returned")

    if 'ID' not in context.table.headings:
        addr_parts = context.response.property_list('address')

    for line in context.table:
        if 'ID' in context.table.headings:
            addr_parts = [dict(context.response.result[int(line['ID'])]['address'])]

        for h in context.table.headings:
            if h != 'ID':
                for p in addr_parts:
                    assert h in p
                    assert p[h] == line[h], "Bad address value for %s" % h

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

    addr_parts = dict(context.response.result[int(lid)]['address'])

    for line in context.table:
        assert line['type'] in addr_parts
        assert addr_parts[line['type']] == line['value'], \
                     "Bad address value for %s" % line['type']
        del addr_parts[line['type']]

    if complete == 'is':
        assert len(addr_parts) == 0, "Additional address parts found: %s" % str(addr_parts)

@then(u'result (?P<lid>\d+ )?has bounding box in (?P<coords>[\d,.-]+)')
def step_impl(context, lid, coords):
    if lid is None:
        context.execute_steps("then at least 1 result is returned")
        bboxes = context.response.property_list('boundingbox')
    else:
        context.execute_steps("then more than %sresults are returned" % lid)
        bboxes = [ context.response.result[int(lid)]['boundingbox']]

    coord = [ float(x) for x in coords.split(',') ]

    for bbox in bboxes:
        if isinstance(bbox, str):
            bbox = bbox.split(',')
        bbox = [ float(x) for x in bbox ]

        assert bbox[0] >= coord[0]
        assert bbox[1] <= coord[1]
        assert bbox[2] >= coord[2]
        assert bbox[3] <= coord[3]

@then(u'result (?P<lid>\d+ )?has centroid in (?P<coords>[\d,.-]+)')
def step_impl(context, lid, coords):
    if lid is None:
        context.execute_steps("then at least 1 result is returned")
        bboxes = zip(context.response.property_list('lat'),
                     context.response.property_list('lon'))
    else:
        context.execute_steps("then more than %sresults are returned" % lid)
        res = context.response.result[int(lid)]
        bboxes = [ (res['lat'], res['lon']) ]

    coord = [ float(x) for x in coords.split(',') ]

    for lat, lon in bboxes:
        lat = float(lat)
        lon = float(lon)
        assert lat >= coord[0]
        assert lat <= coord[1]
        assert lon >= coord[2]
        assert lon <= coord[3]

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
