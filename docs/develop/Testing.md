# Nominatim Test Suite

This chapter describes the tests in the `/test` directory, how they are
structured and how to extend them. For a quick introduction on how to run
the tests, see the [Development setup chapter](Development-Environment.md).

## Overall structure

There are two kind of tests in this test suite. There are functional tests
which test the API interface using a BDD test framework and there are unit
tests for specific PHP functions.

This test directory is sturctured as follows:

```
 -+-   bdd         Functional API tests
  | \
  | +-  steps      Step implementations for test descriptions
  | +-  osm2pgsql  Tests for data import via osm2pgsql
  | +-  db         Tests for internal data processing on import and update
  | +-  api        Tests for API endpoints (search, reverse, etc.)
  |
  +-   php         PHP unit tests
  +-   python      Python unit tests
  +-   testdb      Base data for generating API test database
  +-   testdata    Additional test data used by unit tests
```

## PHP Unit Tests (`test/php`)

Unit tests for PHP code can be found in the `php/` directory. They test selected
PHP functions. Very low coverage.

To execute the test suite run

    cd test/php
    UNIT_TEST_DSN='pgsql:dbname=nominatim_unit_tests' phpunit ../

It will read phpunit.xml which points to the library, test path, bootstrap
strip and sets other parameters.

It will use (and destroy) a local database 'nominatim_unit_tests'. You can set
a different connection string with e.g. UNIT_TEST_DSN='pgsql:dbname=foo_unit_tests'.

## Python Unit Tests (`test/python`)

Unit tests for Python code can be found in the `python/` directory. The goal is
to have complete coverage of the Python library in `nominatim`.

To execute the tests run

    py.test-3 test/python

or

    pytest test/python

The name of the pytest binary depends on your installation.

## BDD Functional Tests (`test/bdd`)

Functional tests are written as BDD instructions. For more information on
the philosophy of BDD testing, see the
[Behave manual](http://pythonhosted.org/behave/philosophy.html).

The following explanation assume that the reader is familiar with the BDD
notations of features, scenarios and steps.

All possible steps can be found in the `steps` directory and should ideally
be documented.

### General Usage

To run the functional tests, do

    cd test/bdd
    behave

The tests can be configured with a set of environment variables (`behave -D key=val`):

 * `BUILDDIR` - build directory of Nominatim installation to test
 * `TEMPLATE_DB` - name of template database used as a skeleton for
                   the test databases (db tests)
 * `TEST_DB` - name of test database (db tests)
 * `API_TEST_DB` - name of the database containing the API test data (api tests)
 * `API_TEST_FILE` - OSM file to be imported into the API test database (api tests)
 * `API_ENGINE` - webframe to use for running search queries, same values as
                  `nominatim serve --engine` parameter
 * `DB_HOST` - (optional) hostname of database host
 * `DB_PORT` - (optional) port of database on host
 * `DB_USER` - (optional) username of database login
 * `DB_PASS` - (optional) password for database login
 * `SERVER_MODULE_PATH` - (optional) path on the Postgres server to Nominatim
                          module shared library file
 * `REMOVE_TEMPLATE` - if true, the template and API database will not be reused
                       during the next run. Reusing the base templates speeds
                       up tests considerably but might lead to outdated errors
                       for some changes in the database layout.
 * `KEEP_TEST_DB` - if true, the test database will not be dropped after a test
                    is finished. Should only be used if one single scenario is
                    run, otherwise the result is undefined.

Logging can be defined through command line parameters of behave itself. Check
out `behave --help` for details. Also have a look at the 'work-in-progress'
feature of behave which comes in handy when writing new tests.

### API Tests (`test/bdd/api`)

These tests are meant to test the different API endpoints and their parameters.
They require to import several datasets into a test database. This is normally
done automatically during setup of the test. The API test database is then
kept around and reused in subsequent runs of behave. Use `behave -DREMOVE_TEMPLATE`
to force a reimport of the database.

The official test dataset is saved in the file `test/testdb/apidb-test-data.pbf`
and compromises the following data:

 * Geofabrik extract of Liechtenstein
 * extract of Autauga country, Alabama, US (for tests against Tiger data)
 * additional data from `test/testdb/additional_api_test.data.osm`

API tests should only be testing the functionality of the website PHP code.
Most tests should be formulated as BDD DB creation tests (see below) instead.

#### Code Coverage (PHP engine only)

The API tests also support code coverage tests. You need to install
[PHP_CodeCoverage](https://github.com/sebastianbergmann/php-code-coverage).
On Debian/Ubuntu run:

    apt-get install php-codecoverage php-xdebug

Then run the API tests as follows:

    behave api -DPHPCOV=<coverage output dir>

The output directory must be an absolute path. To generate reports, you can use
the [phpcov](https://github.com/sebastianbergmann/phpcov) tool:

    phpcov merge --html=<report output dir> <coverage output dir>

### DB Creation Tests (`test/bdd/db`)

These tests check the import and update of the Nominatim database. They do not
test the correctness of osm2pgsql. Each test will write some data into the `place`
table (and optionally the `planet_osm_*` tables if required) and then run
Nominatim's processing functions on that.

These tests need to create their own test databases. By default they will be
called `test_template_nominatim` and `test_nominatim`. Names can be changed with
the environment variables `TEMPLATE_DB` and `TEST_DB`. The user running the tests
needs superuser rights for postgres.

### Import Tests (`test/bdd/osm2pgsql`)

These tests check that data is imported correctly into the place table. They
use the same template database as the DB Creation tests, so the same remarks apply.
