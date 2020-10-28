[![Build Status](https://github.com/osm-search/Nominatim/workflows/CI%20Tests/badge.svg)](https://github.com/osm-search/Nominatim/actions?query=workflow%3A%22CI+Tests%22)

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

**Nominatim is a complex piece of software and runs in a complex environment.
Installing and running Nominatim is something for experienced system
administrators only who can do some trouble-shooting themselves. We are sorry,
but we can not provide installation support. We are all doing this in our free
time and there is just so much of that time to go around. Do not open issues in
our bug tracker if you need help. You can ask questions on the mailing list
(see below) or on [help.openstreetmap.org](https://help.openstreetmap.org/).**

The latest stable release can be downloaded from https://nominatim.org.
There you can also find [installation instructions for the release](https://nominatim.org/release-docs/latest/admin/Installation), as well as an extensive [Troubleshooting/FAQ section](https://nominatim.org/release-docs/latest/admin/Faq/).

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

For questions you can join the geocoding mailing list, see
https://lists.openstreetmap.org/listinfo/geocoding
