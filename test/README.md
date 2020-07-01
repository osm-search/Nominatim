This directory contains functional and unit tests for the Nominatim API.

Prerequisites
=============

See `docs/develop/Setup.md`

Overall structure
=================

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
  +-   scenes      Geometry test data
  +-   testdb      Base data for generating API test database
```

PHP Unit Tests
==============

Unit tests can be found in the php/ directory and tests selected php functions.
Very low coverage.

To execute the test suite run

    cd test/php
    UNIT_TEST_DSN='pgsql:dbname=nominatim_unit_tests' phpunit ../

It will read phpunit.xml which points to the library, test path, bootstrap
strip and set other parameters.

It will use (and destroy) a local database 'nominatim_unit_tests'. You can set
a different connection string with e.g. UNIT_TEST_DSN='pgsql:dbname=foo_unit_tests'.

BDD Functional Tests
====================

Functional tests are written as BDD instructions. For more information on
the philosophy of BDD testing, see http://pythonhosted.org/behave/philosophy.html

Usage
-----

To run the functional tests, do

    cd test/bdd
    behave

The tests can be configured with a set of environment variables (`behave -D key=val`):

 * `BUILDDIR` - build directory of Nominatim installation to test
 * `TEMPLATE_DB` - name of template database used as a skeleton for
                   the test databases (db tests)
 * `TEST_DB` - name of test database (db tests)
 * `API_TEST_DB` - name of the database containing the API test data (api tests)
 * `DB_HOST` - (optional) hostname of database host
 * `DB_PORT` - (optional) port of database on host
 * `DB_USER` - (optional) username of database login
 * `DB_PASS` - (optional) password for database login
 * `SERVER_MODULE_PATH` - (optional) path on the Postgres server to Nominatim
                          module shared library file
 * `TEST_SETTINGS_TEMPLATE` - file to write temporary Nominatim settings to
 * `REMOVE_TEMPLATE` - if true, the template database will not be reused during
                       the next run. Reusing the base templates speeds up tests
                       considerably but might lead to outdated errors for some
                       changes in the database layout.
 * `KEEP_TEST_DB` - if true, the test database will not be dropped after a test
                    is finished. Should only be used if one single scenario is
                    run, otherwise the result is undefined.

Logging can be defined through command line parameters of behave itself. Check
out `behave --help` for details. Also keep an eye out for the 'work-in-progress'
feature of behave which comes in handy when writing new tests.

Writing Tests
-------------

The following explanation assume that the reader is familiar with the BDD
notations of features, scenarios and steps.

All possible steps can be found in the `steps` directory and should ideally
be documented.

### API Tests (`test/bdd/api`)

These tests are meant to test the different API endpoints and their parameters.
They require a to import several datasets into a test database. You need at
least 2GB RAM and 10GB discspace.


1. Fetch the OSM planet extract (200MB). See end of document how it got created.

    ```
    cd Nominatim/data
    mkdir testdb
    cd testdb
    wget https://www.nominatim.org/data/test/nominatim-api-testdata.pbf
    ```

2. Fetch `46*` (South Dakota) Tiger data

    ```
    cd Nominatim/data/testdb
    wget https://nominatim.org/data/tiger2018-nominatim-preprocessed.tar.gz
    tar xvf tiger2018-nominatim-preprocessed.tar.gz --wildcards --no-anchored '46*'
    rm tiger2018-nominatim-preprocessed.tar.gz
    ```

3. Adapt build/settings/local.php settings:

	```
    @define('CONST_Database_DSN', 'pgsql:dbname=test_api_nominatim');
    @define('CONST_Use_US_Tiger_Data', true);
    @define('CONST_Tiger_Data_Path', CONST_ExtraDataPath.'/testdb');
    @define('CONST_Wikipedia_Data_Path', CONST_BasePath.'/test/testdb');
    ```

4. Import

    ```
	LOGFILE=/tmp/nominatim-testdb.$$.log
    dropdb --if-exists test_api_nominatim
    ./utils/setup.php --all --osm-file ../Nominatim/data/testdb/nominatim-api-testdb.pbf 2>&1 | tee $LOGFILE
    ./utils/specialphrases.php --wiki-import > specialphrases.sql
    psql -d test_api_nominatim -f specialphrases.sql 2>&1 | tee -a $LOGFILE
    ./utils/setup.php --import-tiger-data 2>&1 | tee -a $LOGFILE
    ```

#### Code Coverage

The API tests also support code coverage tests. You need to install
[PHP_CodeCoverage](https://github.com/sebastianbergmann/php-code-coverage).
On Debian/Ubuntu run:

    apt-get install php-codecoverage php-xdebug

The run the API tests as follows:

    behave api -DPHPCOV=<coverage output dir>

The output directory must be an absolute path. To generate reports, you can use
the [phpcov](https://github.com/sebastianbergmann/phpcov) tool:

    phpcov merge --html=<report output dir> <coverage output dir>

### Indexing Tests (`test/bdd/db`)

These tests check the import and update of the Nominatim database. They do not
test the correctness of osm2pgsql. Each test will write some data into the `place`
table (and optionally `the planet_osm_*` tables if required) and then run
Nominatim's processing functions on that.

These tests need to create their own test databases. By default they will be
called `test_template_nominatim` and `test_nominatim`. Names can be changed with
the environment variables `TEMPLATE_DB` and `TEST_DB`. The user running the tests
needs superuser rights for postgres.

### Import Tests (`test/bdd/osm2pgsql`)

These tests check that data is imported correctly into the place table. They
use the same template database as the Indexing tests, so the same remarks apply.



How the test database extract was generated
-------------------------------------------
The official test dataset was derived from the 180924 planet (note: such
file no longer exists at https://planet.openstreetmap.org/planet/2018/).
Newer planets are likely to work as well but you may see isolated test
failures where the data has changed. To recreate the input data
for the test database run:

    wget https://ftp5.gwdg.de/pub/misc/openstreetmap/planet.openstreetmap.org/pbf/planet-180924.osm.pbf
    osmconvert planet-180924.osm.pbf -B=test/testdb/testdb.polys -o=testdb.pbf
