""" Steps that run search queries.

    Queries may either be run directly via PHP using the query script
    or via the HTTP interface.
"""

import json
import os
import io
import re
import logging
from tidylib import tidy_document
import xml.etree.ElementTree as ET
import subprocess
from urllib.parse import urlencode
from collections import OrderedDict
from nose.tools import * # for assert functions

logger = logging.getLogger(__name__)

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

class GenericResponse(object):

    def match_row(self, row):
        if 'ID' in row.headings:
            todo = [int(row['ID'])]
        else:
            todo = range(len(self.result))

        for i in todo:
            res = self.result[i]
            for h in row.headings:
                if h == 'ID':
                    pass
                elif h == 'osm':
                    assert_equal(res['osm_type'], row[h][0])
                    assert_equal(res['osm_id'], row[h][1:])
                elif h == 'centroid':
                    x, y = row[h].split(' ')
                    assert_almost_equal(float(y), float(res['lat']))
                    assert_almost_equal(float(x), float(res['lon']))
                elif row[h].startswith("^"):
                    assert_in(h, res)
                    assert_is_not_none(re.fullmatch(row[h], res[h]),
                                       "attribute '%s': expected: '%s', got '%s'"
                                          % (h, row[h], res[h]))
                else:
                    assert_in(h, res)
                    assert_equal(str(res[h]), str(row[h]))

    def property_list(self, prop):
        return [ x[prop] for x in self.result ]


class SearchResponse(GenericResponse):

    def __init__(self, page, fmt='json', errorcode=200):
        self.page = page
        self.format = fmt
        self.errorcode = errorcode
        self.result = []
        self.header = dict()

        if errorcode == 200:
            getattr(self, 'parse_' + fmt)()

    def parse_json(self):
        m = re.fullmatch(r'([\w$][^(]*)\((.*)\)', self.page)
        if m is None:
            code = self.page
        else:
            code = m.group(2)
            self.header['json_func'] = m.group(1)
        self.result = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(code)

    def parse_geojson(self):
        self.parse_json()
        self.result = geojson_results_to_json_results(self.result)

    def parse_geocodejson(self):
        return self.parse_geojson()

    def parse_html(self):
        content, errors = tidy_document(self.page,
                                        options={'char-encoding' : 'utf8'})
        #eq_(len(errors), 0 , "Errors found in HTML document:\n%s" % errors)

        self.result = []
        b = content.find('nominatim_results =')
        e = content.find('</script>')
        if b >= 0 and e >= 0:
            content = content[b:e]

            b = content.find('[')
            e = content.rfind(']')
            if b >= 0 and e >= 0:
                self.result = json.JSONDecoder(object_pairs_hook=OrderedDict)\
                                  .decode(content[b:e+1])

    def parse_xml(self):
        et = ET.fromstring(self.page)

        self.header = dict(et.attrib)

        for child in et:
            assert_equal(child.tag, "place")
            self.result.append(dict(child.attrib))

            address = {}
            for sub in child:
                if sub.tag == 'extratags':
                    self.result[-1]['extratags'] = {}
                    for tag in sub:
                        self.result[-1]['extratags'][tag.attrib['key']] = tag.attrib['value']
                elif sub.tag == 'namedetails':
                    self.result[-1]['namedetails'] = {}
                    for tag in sub:
                        self.result[-1]['namedetails'][tag.attrib['desc']] = tag.text
                elif sub.tag in ('geokml'):
                    self.result[-1][sub.tag] = True
                else:
                    address[sub.tag] = sub.text

            if len(address) > 0:
                self.result[-1]['address'] = address


class ReverseResponse(GenericResponse):

    def __init__(self, page, fmt='json', errorcode=200):
        self.page = page
        self.format = fmt
        self.errorcode = errorcode
        self.result = []
        self.header = dict()

        if errorcode == 200:
            getattr(self, 'parse_' + fmt)()

    def parse_html(self):
        content, errors = tidy_document(self.page,
                                        options={'char-encoding' : 'utf8'})
        #eq_(len(errors), 0 , "Errors found in HTML document:\n%s" % errors)

        b = content.find('nominatim_results =')
        e = content.find('</script>')
        content = content[b:e]
        b = content.find('[')
        e = content.rfind(']')

        self.result = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(content[b:e+1])

    def parse_json(self):
        m = re.fullmatch(r'([\w$][^(]*)\((.*)\)', self.page)
        if m is None:
            code = self.page
        else:
            code = m.group(2)
            self.header['json_func'] = m.group(1)
        self.result = [json.JSONDecoder(object_pairs_hook=OrderedDict).decode(code)]

    def parse_geojson(self):
        self.parse_json()
        if 'error' in self.result:
            return
        self.result = geojson_results_to_json_results(self.result[0])

    def parse_geocodejson(self):
        return self.parse_geojson()

    def parse_xml(self):
        et = ET.fromstring(self.page)

        self.header = dict(et.attrib)
        self.result = []

        for child in et:
            if child.tag == 'result':
                eq_(0, len(self.result), "More than one result in reverse result")
                self.result.append(dict(child.attrib))
            elif child.tag == 'addressparts':
                address = {}
                for sub in child:
                    address[sub.tag] = sub.text
                self.result[0]['address'] = address
            elif child.tag == 'extratags':
                self.result[0]['extratags'] = {}
                for tag in child:
                    self.result[0]['extratags'][tag.attrib['key']] = tag.attrib['value']
            elif child.tag == 'namedetails':
                self.result[0]['namedetails'] = {}
                for tag in child:
                    self.result[0]['namedetails'][tag.attrib['desc']] = tag.text
            elif child.tag in ('geokml'):
                self.result[0][child.tag] = True
            else:
                assert child.tag == 'error', \
                        "Unknown XML tag %s on page: %s" % (child.tag, self.page)


class DetailsResponse(GenericResponse):

    def __init__(self, page, fmt='json', errorcode=200):
        self.page = page
        self.format = fmt
        self.errorcode = errorcode
        self.result = []
        self.header = dict()

        if errorcode == 200:
            getattr(self, 'parse_' + fmt)()

    def parse_html(self):
        content, errors = tidy_document(self.page,
                                        options={'char-encoding' : 'utf8'})
        self.result = {}

    def parse_json(self):
        self.result = [json.JSONDecoder(object_pairs_hook=OrderedDict).decode(self.page)]


class StatusResponse(GenericResponse):

    def __init__(self, page, fmt='text', errorcode=200):
        self.page = page
        self.format = fmt
        self.errorcode = errorcode

        if errorcode == 200 and fmt != 'text':
            getattr(self, 'parse_' + fmt)()

    def parse_json(self):
        self.result = [json.JSONDecoder(object_pairs_hook=OrderedDict).decode(self.page)]


def geojson_result_to_json_result(geojson_result):
    result = geojson_result['properties']
    result['geojson'] = geojson_result['geometry']
    if 'bbox' in geojson_result:
        # bbox is  minlon, minlat, maxlon, maxlat
        # boundingbox is minlat, maxlat, minlon, maxlon
        result['boundingbox'] = [
                                    geojson_result['bbox'][1],
                                    geojson_result['bbox'][3],
                                    geojson_result['bbox'][0],
                                    geojson_result['bbox'][2]
                                ]
    return result


def geojson_results_to_json_results(geojson_results):
    if 'error' in geojson_results:
        return
    return list(map(geojson_result_to_json_result, geojson_results['features']))


@when(u'searching for "(?P<query>.*)"(?P<dups> with dups)?')
def query_cmd(context, query, dups):
    """ Query directly via PHP script.
    """
    cmd = ['/usr/bin/env', 'php']
    cmd.append(os.path.join(context.nominatim.build_dir, 'utils', 'query.php'))
    cmd.extend(['--search', query])
    # add more parameters in table form
    if context.table:
        for h in context.table.headings:
            value = context.table[0][h].strip()
            if value:
                cmd.extend(('--' + h, value))

    if dups:
        cmd.extend(('--dedupe', '0'))

    proc = subprocess.Popen(cmd, cwd=context.nominatim.build_dir,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    (outp, err) = proc.communicate()

    assert_equals (0, proc.returncode, "query.php failed with message: %s\noutput: %s" % (err, outp))

    context.response = SearchResponse(outp.decode('utf-8'), 'json')

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
    env['CONTEXT_DOCUMENT_ROOT'] = os.path.join(context.nominatim.build_dir, 'website')
    env['SCRIPT_FILENAME'] = os.path.join(env['CONTEXT_DOCUMENT_ROOT'],
                                          '%s.php' % endpoint)
    env['NOMINATIM_SETTINGS'] = context.nominatim.local_settings_file

    logger.debug("Environment:" + json.dumps(env, sort_keys=True, indent=2))

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

    proc = subprocess.Popen(cmd, cwd=context.nominatim.build_dir, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    (outp, err) = proc.communicate()
    outp = outp.decode('utf-8')
    err = err.decode("utf-8")

    logger.debug("Result: \n===============================\n"
                 + outp + "\n===============================\n")

    assert_equals(0, proc.returncode,
                  "%s failed with message: %s" % (
                      os.path.basename(env['SCRIPT_FILENAME']),
                      err))

    assert_equals(0, len(err), "Unexpected PHP error: %s" % (err))

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

    if fmt is None:
        outfmt = 'html'
    elif fmt == 'jsonv2 ':
        outfmt = 'json'
    else:
        outfmt = fmt.strip()

    context.response = SearchResponse(outp, outfmt, status)

@when(u'sending (?P<fmt>\S+ )?reverse coordinates (?P<lat>.+)?,(?P<lon>.+)?')
def website_reverse_request(context, fmt, lat, lon):
    params = {}
    if lat is not None:
        params['lat'] = lat
    if lon is not None:
        params['lon'] = lon

    outp, status = send_api_query('reverse', params, fmt, context)

    if fmt is None:
        outfmt = 'xml'
    elif fmt == 'jsonv2 ':
        outfmt = 'json'
    else:
        outfmt = fmt.strip()

    context.response = ReverseResponse(outp, outfmt, status)

@when(u'sending (?P<fmt>\S+ )?details query for (?P<query>.*)')
def website_details_request(context, fmt, query):
    params = {}
    if query[0] in 'NWR':
        params['osmtype'] = query[0]
        params['osmid'] = query[1:]
    else:
        params['place_id'] = query
    outp, status = send_api_query('details', params, fmt, context)

    if fmt is None:
        outfmt = 'html'
    else:
        outfmt = fmt.strip()

    context.response = DetailsResponse(outp, outfmt, status)

@when(u'sending (?P<fmt>\S+ )?lookup query for (?P<query>.*)')
def website_lookup_request(context, fmt, query):
    params = { 'osm_ids' : query }
    outp, status = send_api_query('lookup', params, fmt, context)

    if fmt == 'json ':
        outfmt = 'json'
    elif fmt == 'geojson ':
        outfmt = 'geojson'
    else:
        outfmt = 'xml'

    context.response = SearchResponse(outp, outfmt, status)

@when(u'sending (?P<fmt>\S+ )?status query')
def website_status_request(context, fmt):
    params = {}
    outp, status = send_api_query('status', params, fmt, context)

    if fmt is None:
        outfmt = 'text'
    else:
        outfmt = fmt.strip()

    context.response = StatusResponse(outp, outfmt, status)

@step(u'(?P<operator>less than|more than|exactly|at least|at most) (?P<number>\d+) results? (?:is|are) returned')
def validate_result_number(context, operator, number):
    eq_(context.response.errorcode, 200)
    numres = len(context.response.result)
    ok_(compare(operator, numres, int(number)),
        "Bad number of results: expected %s %s, got %d." % (operator, number, numres))

@then(u'a HTTP (?P<status>\d+) is returned')
def check_http_return_status(context, status):
    eq_(context.response.errorcode, int(status))

@then(u'the page contents equals "(?P<text>.+)"')
def check_page_content_equals(context, text):
    eq_(context.response.page, text)

@then(u'the result is valid (?P<fmt>\w+)')
def step_impl(context, fmt):
    context.execute_steps("Then a HTTP 200 is returned")
    eq_(context.response.format, fmt)

@then(u'a (?P<fmt>\w+) user error is returned')
def check_page_error(context, fmt):
    context.execute_steps("Then a HTTP 400 is returned")
    eq_(context.response.format, fmt)

    if fmt == 'html':
        assert_is_not_none(re.search(r'<html( |>).+</html>', context.response.page, re.DOTALL))
    elif fmt == 'xml':
        assert_is_not_none(re.search(r'<error>.+</error>', context.response.page, re.DOTALL))
    else:
        assert_is_not_none(re.search(r'({"error":)', context.response.page, re.DOTALL))

@then(u'result header contains')
def check_header_attr(context):
    for line in context.table:
        assert_is_not_none(re.fullmatch(line['value'], context.response.header[line['attr']]),
                     "attribute '%s': expected: '%s', got '%s'"
                       % (line['attr'], line['value'],
                          context.response.header[line['attr']]))

@then(u'result header has (?P<neg>not )?attributes (?P<attrs>.*)')
def check_header_no_attr(context, neg, attrs):
    for attr in attrs.split(','):
        if neg:
            assert_not_in(attr, context.response.header)
        else:
            assert_in(attr, context.response.header)

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
                assert_not_in(attr, context.response.result[i])
            else:
                assert_in(attr, context.response.result[i])

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
                    assert_in(h, p)
                    assert_equal(p[h], line[h], "Bad address value for %s" % h)

@then(u'address of result (?P<lid>\d+) has(?P<neg> no)? types (?P<attrs>.*)')
def check_address(context, lid, neg, attrs):
    context.execute_steps("then more than %s results are returned" % lid)

    addr_parts = context.response.result[int(lid)]['address']

    for attr in attrs.split(','):
        if neg:
            assert_not_in(attr, addr_parts)
        else:
            assert_in(attr, addr_parts)

@then(u'address of result (?P<lid>\d+) is')
def check_address(context, lid):
    context.execute_steps("then more than %s results are returned" % lid)

    addr_parts = dict(context.response.result[int(lid)]['address'])

    for line in context.table:
        assert_in(line['type'], addr_parts)
        assert_equal(addr_parts[line['type']], line['value'],
                     "Bad address value for %s" % line['type'])
        del addr_parts[line['type']]

    eq_(0, len(addr_parts), "Additional address parts found: %s" % str(addr_parts))

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

        assert_greater_equal(bbox[0], coord[0])
        assert_less_equal(bbox[1], coord[1])
        assert_greater_equal(bbox[2], coord[2])
        assert_less_equal(bbox[3], coord[3])

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
        assert_greater_equal(lat, coord[0])
        assert_less_equal(lat, coord[1])
        assert_greater_equal(lon, coord[2])
        assert_less_equal(lon, coord[3])

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
