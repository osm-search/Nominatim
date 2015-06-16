""" Steps for checking the results of queries.
"""

from nose.tools import *
from lettuce import *
from tidylib import tidy_document
from collections import OrderedDict
import json
import logging
import re
from xml.dom.minidom import parseString

logger = logging.getLogger(__name__)

def _parse_xml():
    """ Puts the DOM structure into more convenient python
        with a similar structure as the json document, so
        that the same the semantics can be used. It does not
        check if the content is valid (or at least not more than
        necessary to transform it into a dict structure).
    """
    page = parseString(world.page).documentElement

    # header info
    world.result_header = OrderedDict(page.attributes.items())
    logger.debug('Result header: %r' % (world.result_header))
    world.results = []

    # results
    if page.nodeName == 'searchresults':
        for node in page.childNodes:
            if node.nodeName != "#text":
                assert_equals(node.nodeName, 'place', msg="Unexpected element '%s'" % node.nodeName)
                newresult = OrderedDict(node.attributes.items())
                assert_not_in('address', newresult)
                assert_not_in('geokml', newresult)
                address = OrderedDict()
                for sub in node.childNodes:
                    if sub.nodeName == 'geokml':
                        newresult['geokml'] = sub.childNodes[0].toxml()
                    elif sub.nodeName == '#text':
                        pass
                    else:
                        address[sub.nodeName] = sub.firstChild.nodeValue.strip()
                if address:
                    newresult['address'] = address
                world.results.append(newresult)
    elif page.nodeName == 'reversegeocode':
        haserror = False
        address = {}
        for node in page.childNodes:
            if node.nodeName == 'result':
                assert_equals(len(world.results), 0)
                assert (not haserror)
                world.results.append(OrderedDict(node.attributes.items()))
                assert_not_in('display_name', world.results[0])
                assert_not_in('address', world.results[0])
                world.results[0]['display_name'] = node.firstChild.nodeValue.strip()
            elif node.nodeName == 'error':
                assert_equals(len(world.results), 0)
                haserror = True
            elif node.nodeName == 'addressparts':
                assert (not haserror)
                address = OrderedDict()
                for sub in node.childNodes:
                    address[sub.nodeName] = sub.firstChild.nodeValue.strip()
                world.results[0]['address'] = address
            elif node.nodeName == "#text":
                pass
            else:
                assert False, "Unknown content '%s' in XML" % node.nodeName
    else:
        assert False, "Unknown document node name %s in XML" % page.nodeName

    logger.debug("The following was parsed out of XML:")
    logger.debug(world.results)

@step(u'a HTTP (\d+) is returned')
def api_result_http_error(step, error):
    assert_equals(world.returncode, int(error))

@step(u'the result is valid( \w+)?')
def api_result_is_valid(step, fmt):
    assert_equals(world.returncode, 200)

    if world.response_format == 'html':
        document, errors = tidy_document(world.page, 
                             options={'char-encoding' : 'utf8'})
        assert(len(errors) == 0), "Errors found in HTML document:\n%s" % errors
        world.results = document
    elif world.response_format == 'xml':
        _parse_xml()
    elif world.response_format == 'json':
        world.results = json.JSONDecoder(object_pairs_hook=OrderedDict).decode(world.page)
    else:
        assert False, "Unknown page format: %s" % (world.response_format)

    if fmt:
        assert_equals (fmt.strip(), world.response_format)


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

@step(u'(less than|more than|exactly|at least|at most) (\d+) results? (?:is|are) returned')
def validate_result_number(step, operator, number):
    step.given('the result is valid')
    numres = len(world.results)
    assert compare(operator, numres, int(number)), \
        "Bad number of results: expected %s %s, got %d." % (operator, number, numres)

@step(u'result (\d+) has( not)? attributes (\S+)')
def search_check_for_result_attribute(step, num, invalid, attrs):
    num = int(num)
    step.given('at least %d results are returned' % (num + 1))
    res = world.results[num]
    for attr in attrs.split(','):
        if invalid:
            assert_not_in(attr.strip(), res)
        else:
            assert_in(attr.strip(),res)
        
@step(u'there is a json wrapper "([^"]*)"')
def api_result_check_json_wrapper(step, wrapper):
    step.given('the result is valid json')
    assert_equals(world.json_callback, wrapper)

@step(u'result header contains')
def api_result_header_contains(step):
    step.given('the result is valid')
    for line in step.hashes:
        assert_in(line['attr'], world.result_header)
        m = re.match("%s$" % (line['value'],), world.result_header[line['attr']])

@step(u'result header has no attribute (.*)')
def api_result_header_contains_not(step, attr):
    step.given('the result is valid')
    assert_not_in(attr, world.result_header)

@step(u'results contain$')
def api_result_contains(step):
    step.given('at least 1 result is returned')
    for line in step.hashes:
        if 'ID' in line:
            reslist = (world.results[int(line['ID'])],)
        else:
            reslist = world.results
        for k,v in line.iteritems():
            if k == 'latlon':
                for curres in reslist:
                    world.match_geometry((float(curres['lat']), float(curres['lon'])), v)
            elif k != 'ID':
                for curres in reslist:
                    assert_in(k, curres)
                    if v[0] in '<>=':
                        # mathematical operation
                        evalexp = '%s %s' % (curres[k], v)
                        res = eval(evalexp)
                        logger.debug('Evaluating: %s = %s' % (res, evalexp))
                        assert_true(res, "Evaluation failed: %s" % (evalexp, ))
                    else:
                        # regex match
                        m = re.match("%s$" % (v,), curres[k])
                        assert_is_not_none(m, msg="field %s does not match: %s$ != %s." % (k, v, curres[k]))


@step(u'result addresses contain$')
def api_result_address_contains(step):
    step.given('the result is valid')
    for line in step.hashes:
        if 'ID' in line:
            reslist = (world.results[int(line['ID'])],)
        else:
            reslist = world.results
        for k,v in line.iteritems():
            if k != 'ID':
                for res in reslist:
                    curres = res['address']
                    assert_in(k, curres)
                    m = re.match("%s$" % (v,), curres[k])
                    assert_is_not_none(m, msg="field %s does not match: %s$ != %s." % (k, v, curres[k]))


@step(u'address of result (\d+) contains')
def api_result_address_exact(step, resid):
    resid = int(resid)
    step.given('at least %d results are returned' % (resid + 1))
    addr = world.results[resid]['address']
    for line in step.hashes:
        assert_in(line['type'], addr)
        m = re.match("%s$" % line['value'], addr[line['type']])
        assert_is_not_none(m, msg="field %s does not match: %s$ != %s." % (
                                  line['type'], line['value'], addr[line['type']]))
        #assert_equals(line['value'], addr[line['type']])

@step(u'address of result (\d+) does not contain (.*)')
def api_result_address_details_missing(step, resid, types):
    resid = int(resid)
    step.given('at least %d results are returned' % (resid + 1))
    addr = world.results[resid]['address']
    for t in types.split(','):
        assert_not_in(t.strip(), addr)


@step(u'address of result (\d+) is')
def api_result_address_exact(step, resid):
    resid = int(resid)
    step.given('at least %d results are returned' % (resid + 1))
    result = world.results[resid]
    linenr = 0
    assert_equals(len(step.hashes), len(result['address']))
    for k,v in result['address'].iteritems():
        assert_equals(step.hashes[linenr]['type'], k)
        assert_equals(step.hashes[linenr]['value'], v)
        linenr += 1


@step('there are( no)? duplicates')
def api_result_check_for_duplicates(step, nodups=None):
    step.given('at least 1 result is returned')
    resarr = []
    for res in world.results:
        resarr.append((res['osm_type'], res['class'],
                        res['type'], res['display_name']))

    if nodups is None:
        assert len(resarr) > len(set(resarr))
    else:
        assert_equal(len(resarr), len(set(resarr)))
