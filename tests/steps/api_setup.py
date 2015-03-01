""" Steps for setting up and sending API requests.
"""

from nose.tools import *
from lettuce import *
import urllib
import urllib2
import logging

logger = logging.getLogger(__name__)

def api_call(requesttype):
    world.json_callback = None
    data = urllib.urlencode(world.params)
    url = "%s/%s?%s" % (world.config.base_url, requesttype, data)
    req = urllib2.Request(url=url, headers=world.header)
    try:
        fd = urllib2.urlopen(req)
        world.page = fd.read()
        world.returncode = 200
    except urllib2.HTTPError, ex:
        world.returncode = ex.code
        world.page = None
        return

    pageinfo = fd.info()
    assert_equal('utf-8', pageinfo.getparam('charset').lower())
    pagetype = pageinfo.gettype()

    fmt = world.params.get('format')
    if fmt == 'html':
        assert_equals('text/html', pagetype)
        world.response_format = fmt
    elif fmt == 'xml':
        assert_equals('text/xml', pagetype)
        world.response_format = fmt
    elif fmt in ('json', 'jsonv2'):
        if 'json_callback' in world.params:
            world.json_callback = world.params['json_callback']
            assert world.page.startswith(world.json_callback + '(')
            assert world.page.endswith(')')
            world.page = world.page[(len(world.json_callback)+1):-1]
            assert_equals('application/javascript', pagetype)
        else:
            assert_equals('application/json', pagetype)
        world.response_format = 'json'
    else:
        if requesttype == 'reverse':
            assert_equals('text/xml', pagetype)
            world.response_format = 'xml'
        else:
            assert_equals('text/html', pagetype)
            world.response_format = 'html'
    logger.debug("Page received (%s):" % world.response_format)
    logger.debug(world.page)

    api_setup_prepare_params(None)

@before.each_scenario
def api_setup_prepare_params(scenario):
    world.results = []
    world.params = {}
    world.header = {}

@step(u'the request parameters$')
def api_setup_parameters(step):
    """Define the parameters of the request as a hash.
       Resets parameter list.
    """
    world.params = step.hashes[0]

@step(u'the HTTP header$')
def api_setup_parameters(step):
    """Define additional HTTP header parameters as a hash.
       Resets parameter list.
    """
    world.header = step.hashes[0]


@step(u'sending( \w+)? search query "([^"]*)"( with address)?')
def api_setup_search(step, fmt, query, doaddr):
    world.params['q'] = query.encode('utf8')
    if doaddr:
        world.params['addressdetails'] = 1
    if fmt:
        world.params['format'] = fmt.strip()
    api_call('search')

@step(u'sending( \w+)? structured query( with address)?$')
def api_setup_structured_search(step, fmt, doaddr):
    world.params.update(step.hashes[0])
    if doaddr:
        world.params['addressdetails'] = 1
    if fmt:
        world.params['format'] = fmt.strip()
    api_call('search')

@step(u'looking up (\w+ )?coordinates ([-\d.]+),([-\d.]+)')
def api_setup_reverse(step, fmt, lat, lon):
    world.params['lat'] = lat
    world.params['lon'] = lon
    if fmt and fmt.strip():
        world.params['format'] = fmt.strip()
    api_call('reverse')

@step(u'looking up place ([NRW]?\d+)')
def api_setup_details_reverse(step, obj):
    if obj[0] in ('N', 'R', 'W'):
        # an osm id
        world.params['osm_type']  = obj[0]
        world.params['osm_id'] = obj[1:]
    else:
        world.params['place_id']  = obj
    api_call('reverse')

@step(u'looking up places (([NRW]\d,?)+)')
def api_setup_details_places(step, obj):
    world.params['osm_ids'] = obj
    api_call('places')

@step(u'looking up details for ([NRW]?\d+)')
def api_setup_details(step, obj):
    if obj[0] in ('N', 'R', 'W'):
        # an osm id
        world.params['osmtype']  = obj[0]
        world.params['osmid'] = obj[1:]
    else:
        world.params['place_id']  = obj
    api_call('details')
