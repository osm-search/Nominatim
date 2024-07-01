# Nominatim - DB Backend

Nominatim is a tool to search OpenStreetMap data
by name and address (geocoding) and to generate synthetic addresses of
OSM points (reverse geocoding).

This module implements the database backend for Nominatim and the
command-line tool for importing and maintaining the database.

## Installation

### Prerequisites

Nominatim requires [osm2pgsql](https://osm2pgsql.org/) (>=1.8) for reading
OSM data and [PostgreSQL](https://www.postgresql.org/) (>=9.6) to store the data.

On Ubuntu (>=23.04) and Debian (when using backports), you can install them with:

    sudo apt-get install osm2pgsql postgresql-postgis

### Installation from pypi

To install Nominatim from pypi, run:

    pip install nominatim-db


## Quick start

First create a project directory for your new Nominatim database, which
is the space for additional configuration and customization:

    mkdir nominatim-project

Make sure you run all nominatim commands from within the project directory:

    cd nominatim-project

Download an appropriate data extract, for example from
[Geofabrik](https://download.geofabrik.de/) and import the file:

    nominatim import --osm-file <downlaoded-osm-data.pbf>

You will need to install the [`nominatim-api`](https://pypi.org/project/nominatim-api/)
package to query the database.

## Documentation

A HTML version of the documentation can be found at
https://nominatim.org/release-docs/latest/ .

## License

The source code is available under a GPLv3 license.
