This directory contains functional tests for the Nominatim API,
for the import/update from osm files and for indexing.

The tests use the lettuce framework (http://lettuce.it/) and
nose (https://nose.readthedocs.org). API tests are meant to be run
against a Nominatim installation with a complete planet-wide
setup based on a fairly recent planet. If you only have an
excerpt, some of the API tests may fail. Database tests can be
run without having a database installed.

Prerequisites
=============

 * lettuce framework (http://lettuce.it/)
 * nose (https://nose.readthedocs.org)
 * pytidylib (http://countergram.com/open-source/pytidylib)
 * haversine (https://github.com/mapado/haversine)

Usage
=====

 * get prerequisites

     [sudo] pip install lettuce nose pytidylib haversine psycopg2

 * run the tests

     NOMINATIM_SERVER=http://your.nominatim.instance/ lettuce features

The tests can be configured with a set of environment variables:

 * `NOMINATIM_SERVER` - URL of the nominatim instance (API tests)
 * `NOMINATIM_DIR` - source directory of Nominatim (import tests)
 * `TEMPLATE_DB` - name of template database used as a skeleton for
                   the test databases (db tests)
 * `TEST_DB` - name of test database (db tests)
 * `NOMINATIM_SETTINGS` - file to write temporary Nominatim settings to (db tests)
 * `NOMINATIM_REUSE_TEMPLATE` - if defined, the template database will not be
                                deleted after the test runs and reused during
                                the next run. This speeds up tests considerably
                                but might lead to outdated errors for some
                                changes in the database layout.
 * `NOMINATIM_KEEP_SCENARIO_DB` - if defined, the test database will not be
                                  dropped after a test is finished. Should
                                  only be used if one single scenario is run,
                                  otherwise the result is undefined.
 * `LOGLEVEL` - set to 'debug' to get more verbose output (only works properly
                when output to a logfile is configured)
 * `LOGFILE` - sends debug output to the given file

Writing Tests
=============

The following explanation assume that the reader is familiar with the lettuce
notations of features, scenarios and steps.

All possible steps can be found in the `steps` directory and should ideally
be documented.


API Tests (`features/api`)
--------------------------

These tests are meant to test the different API calls and their parameters.

There are two kind of steps defined for these tests: 
request setup steps (see `steps/api_setup.py`) 
and steps for checking results (see `steps/api_result.py`).

Each scenario follows this simple sequence of steps:

  1. One or more steps to define parameters and HTTP headers of the request.
     These are cumulative, so you can use multiple steps.
  2. A single step to call the API. This sends a HTTP request to the configured
     server and collects the answer. The cached parameters will be deleted,
     to ensure that the setup works properly with scenario outlines.
  3. As many result checks as necessary. The result remains cached, so that
     multiple tests can be added here.

Indexing Tests (`features/db`)
---------------------------------------------------

These tests check the import and update of the Nominatim database. They do not
test the correctness of osm2pgsql. Each test will write some data into the `place`
table (and optionally `the planet_osm_*` tables if required) and then run
Nominatim's processing functions on that.

These tests need to create their own test databases. By default they will be
called `test_template_nominatim` and `test_nominatim`. Names can be changed with
the environment variables `TEMPLATE_DB` and `TEST_DB`. The user running the tests
needs superuser rights for postgres.


Import Tests (`features/osm2pgsql`)
-----------------------------------

These tests check that data is imported correctly into the place table. They
use the same template database as the Indexing tests, so the same remarks apply.
