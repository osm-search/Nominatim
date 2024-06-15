# Nominatim - Frontend Library

Nominatim is a tool to search OpenStreetMap data
by name and address (geocoding) and to generate synthetic addresses of
OSM points (reverse geocoding).

This module implements the library for searching in a Nominatim database
imported with the 'nominatim-db' package.

## Installation

To install the Nominatim API from pypi, run:

    pip install nominatim-api

## Running a Nominatim server

You need falcon or starlette to run Nominatim as a service, as well as
an ASGI-capable server like uvicorn. To install them from pypi run:

    pip install falcon uvicorn

You need to have a Nominatim database imported with the 'nominatim-db'
package. Go to the project directory, then run uvicorn as:

    uvicorn --factory nominatim.server.falcon.server:run_wsgi

## Documentation

The full documentation for the Nominatim library can be found at:
https://nominatim.org/release-docs/develop/library/Getting-Started/

The v1 API of the server is documented at:
https://nominatim.org/release-docs/develop/api/Overview/

## License

The source code is available under a GPLv3 license.
