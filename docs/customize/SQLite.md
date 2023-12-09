A Nominatim database can be converted into an SQLite database and used as
a read-only source for geocoding queries. This sections describes how to
create and use an SQLite database.

!!! danger
    This feature is in an experimental state at the moment. Use at your own
    risk.

## Installing prerequisites

To use a SQLite database, you need to install:

* SQLite (>= 3.30)
* Spatialite (> 5.0.0)

On Ubuntu/Debian, you can run:

    sudo apt install sqlite3 libsqlite3-mod-spatialite libspatialite7

## Creating a new SQLite database

Nominatim cannot import directly into SQLite database. Instead you have to
first create a geocoding database in PostgreSQL by running a
[regular Nominatim import](../admin/Import.md).

Once this is done, the database can be converted to SQLite with

    nominatim convert -o mydb.sqlite

This will create a database where all geocoding functions are available.
Depending on what functions you need, the database can be made smaller:

* `--without-reverse` omits indexes only needed for reverse geocoding
* `--without-search` omit tables and indexes used for forward search
* `--without-details` leaves out extra information only available in the
  details API

## Using an SQLite database

Once you have created the database, you can use it by simply pointing the
database DSN to the SQLite file:

    NOMINATIM_DATABASE_DSN=sqlite:dbname=mydb.sqlite

Please note that SQLite support is only available for the Python frontend. To
use the test server with an SQLite database, you therefore need to switch
the frontend engine:

    nominatim serve --engine falcon

You need to install falcon or starlette for this, depending on which engine
you choose.

The CLI query commands and the library interface already use the new Python
frontend and therefore work right out of the box.
