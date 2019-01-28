[![Build Status](https://travis-ci.org/openstreetmap/Nominatim.svg?branch=master)](https://travis-ci.org/openstreetmap/Nominatim)

Nominatim
=========

Nominatim (from the Latin, 'by name') is a tool to search OpenStreetMap data
by name and address (geocoding) and to generate synthetic addresses of
OSM points (reverse geocoding). An instance with up-to-date data can be found
at https://nominatim.openstreetmap.org. Nominatim is also used as one of the
sources for the Search box on the OpenStreetMap home page.

Documentation
=============

The documentation of the latest development version is in the
`docs/` subdirectory. A HTML version can be found at
https://nominatim.org/release-docs/develop/ .

Installation
============

The latest stable release can be downloaded from https://nominatim.org.
There you can also find [installation instructions for the release](https://nominatim.org/release-docs/latest/admin/Installation).

Detailed installation instructions for the development version can be
found at [nominatim.org](https://nominatim.org/release-docs/develop/admin/Installation)
as well.

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


Contributing
============

Contributions are welcome. For details see [contribution guide](CONTRIBUTING.md).

Both bug reports and pull requests are welcome.


Mailing list
============

For questions you can join the geocoding mailinglist, see
https://lists.openstreetmap.org/listinfo/geocoding
