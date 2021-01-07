from behave import *
from pathlib import Path

from steps.geometry_factory import GeometryFactory
from steps.nominatim_environment import NominatimEnvironment

TEST_BASE_DIR = Path(__file__) / '..' / '..'

userconfig = {
    'BUILDDIR' : (TEST_BASE_DIR / '..' / 'build').resolve(),
    'REMOVE_TEMPLATE' : False,
    'KEEP_TEST_DB' : False,
    'DB_HOST' : None,
    'DB_PORT' : None,
    'DB_USER' : None,
    'DB_PASS' : None,
    'TEMPLATE_DB' : 'test_template_nominatim',
    'TEST_DB' : 'test_nominatim',
    'API_TEST_DB' : 'test_api_nominatim',
    'API_TEST_FILE'  : (TEST_BASE_DIR / 'testdb' / 'apidb-test-data.pbf').resolve(),
    'SERVER_MODULE_PATH' : None,
    'PHPCOV' : False, # set to output directory to enable code coverage
}

use_step_matcher("re")

def before_all(context):
    # logging setup
    context.config.setup_logging()
    # set up -D options
    for k,v in userconfig.items():
        context.config.userdata.setdefault(k, v)
    # Nominatim test setup
    context.nominatim = NominatimEnvironment(context.config.userdata)
    context.osm = GeometryFactory()


def before_scenario(context, scenario):
    if 'DB' in context.tags:
        context.nominatim.setup_db(context)
    elif 'APIDB' in context.tags:
        context.nominatim.setup_api_db()
    elif 'UNKNOWNDB' in context.tags:
        context.nominatim.setup_unknown_db()
    context.scene = None

def after_scenario(context, scenario):
    if 'DB' in context.tags:
        context.nominatim.teardown_db(context)
