[![Build Status](https://travis-ci.org/openstreetmap/Nominatim.svg?branch=master)](https://travis-ci.org/openstreetmap/Nominatim)

Nominatim
=========

Nominatim (from the Latin, 'by name') is a tool to search OpenStreetMap data
by name and address (geocoding) and to generate synthetic addresses of
OSM points (reverse geocoding). An instance with up-to-date data can be found
at https://nominatim.openstreetmap.org. Nominatim is also used as one of the
sources for the Search box on the OpenStreetMap home page and powers the search
on the MapQuest Open Initiative websites.

Documentation
=============

More information about Nominatim, including usage and installation instructions,
can be found in the docs/ subdirectory and in the OSM wiki at:

https://nominatim.org

Installation
============

The latest stable release can be downloaded from https://nominatim.org.
There you can also find [installation instructions for the release](https://nominatim.org/release-docs/latest/Installation).

Detailed installation instructions for the development version can be
found in the `/docs` directory, see [docs/Installation.md](docs/Installation.md).

A quick summary of the necessary steps:

1. Compile Nominatim:

        mkdir build
        cd build
        cmake ..
        make

2. Get OSM data and import:

        ./build/utils/setup.php --osm-file <your planet file> --all

3. Point your webserver to the ./build/website directory.


License
=======

The source code is available under a GPLv2 license.

Contact and Bug reports
======================

For questions you can join the geocoding mailinglist, see
https://lists.openstreetmap.org/listinfo/geocoding

Bugs may be reported on the github project site:
https://github.com/openstreetmap/Nominatim
