# Nominatim Test Suite

This chapter describes the tests in the `/test` directory, how they are
structured and how to extend them. For a quick introduction on how to run
the tests, see the [Development setup chapter](Development-Environment.md).

## Overall structure

There are two kind of tests in this test suite. There are functional tests
which test the API interface using a BDD test framework and there are unit
tests for the Python code.

This test directory is structured as follows:

```
 -+-   bdd         Functional API tests
  | \
  | +-  steps      Step implementations for test descriptions
  | +-  osm2pgsql  Tests for data import via osm2pgsql
  | +-  db         Tests for internal data processing on import and update
  | +-  api        Tests for API endpoints (search, reverse, etc.)
  |
  +-   python      Python unit tests
  +-   testdb      Base data for generating API test database
  +-   testdata    Additional test data used by unit tests
```

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
the philosophy of BDD testing, read the Wikipedia article on
[Behaviour-driven development](https://en.wikipedia.org/wiki/Behavior-driven_development).

### General Usage

To run the functional tests, do

    pytest test/bdd

The BDD tests create databases for the tests. You can set name of the databases
through configuration variables in your `pytest.ini`:

 * `nominatim_test_db` defines the name of the temporary database created for
    a single test (default: `test_nominatim`)
 * `nominatim_api_test_db` defines the name of the database containing
    the API test data, see also below (default: `test_api_nominatim`)
 * `nominatim_template_db` defines the name of the template database used
    for creating the temporary test databases. It contains some static setup
    which usually doesn't change between imports of OSM data
    (default: `test_template_nominatim`)

To change other connection parameters for the PostgreSQL database, use
the [libpq enivronment variables](https://www.postgresql.org/docs/current/libpq-envars.html).
Never set a password through these variables. Use a
[password file](https://www.postgresql.org/docs/current/libpq-pgpass.html) instead.

The API test database and the template database are only created once and then
left untouched. This is usually what you want because it speeds up subsequent
runs of BDD tests. If you do change code that has an influence on the content
of these databases, you can run pytest with the `--nominatim-purge` parameter
and the databases will be dropped and recreated from scratch.

When running the BDD tests with make (using `make tests` or `make bdd`), then
the databases will always be purged.

The temporary test database is usually dropped directly after the test, so
it does not take up unnecessary space. If you want to keep the database around,
for example while debugging a specific BDD test, use the parameter
`--nominatim-keep-db`.


### API Tests (`test/bdd/api`)

These tests are meant to test the different API endpoints and their parameters.
They require to import several datasets into a test database. This is normally
done automatically during setup of the test. The API test database is then
kept around and reused in subsequent runs of behave. Use `--nominatim-purge`
to force a reimport of the database.

The official test dataset is saved in the file `test/testdb/apidb-test-data.pbf`
and compromises the following data:

 * Geofabrik extract of Liechtenstein
 * extract of Autauga country, Alabama, US (for tests against Tiger data)
 * additional data from `test/testdb/additional_api_test.data.osm`

API tests should only be testing the functionality of the website frontend code.
Most tests should be formulated as BDD DB creation tests (see below) instead.

### DB Creation Tests (`test/bdd/db`)

These tests check the import and update of the Nominatim database. They do not
test the correctness of osm2pgsql. Each test will write some data into the `place`
table (and optionally the `planet_osm_*` tables if required) and then run
Nominatim's processing functions on that.

These tests use the template database and create temporary test databases for
each test.

### Import Tests (`test/bdd/osm2pgsql`)

These tests check that data is imported correctly into the place table.

These tests also use the template database and create temporary test databases
for each test.
