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
our bug tracker if you need help. Use the discussions forum
or ask for help on [help.openstreetmap.org](https://help.openstreetmap.org/).**

The latest stable release can be downloaded from https://nominatim.org.
There you can also find [installation instructions for the release](https://nominatim.org/release-docs/latest/admin/Installation), as well as an extensive [Troubleshooting/FAQ section](https://nominatim.org/release-docs/latest/admin/Faq/).

[Detailed installation instructions for current master](https://nominatim.org/release-docs/develop/admin/Installation)
can be found at nominatim.org as well.

A quick summary of the necessary steps:

1. Compile Nominatim:

        mkdir build
        cd build
        cmake ..
        make

2. Create a project directory, get OSM data and import:

        mkdir nominatim-project
        cd nominatim-project
        ~/build/nominatim import --osm-file <your planet file>

3. Point your webserver to the nominatim-project/website directory.


License
=======

The source code is available under a GPLv2 license.


Contributing
============

Contributions, bugreport and pull requests are welcome.
For details see [contribution guide](CONTRIBUTING.md).


Questions and help
==================

For questions, community help and discussions you can use the
[Github discussions forum](https://github.com/osm-search/Nominatim/discussions)
or join the
[geocoding mailing list](https://lists.openstreetmap.org/listinfo/geocoding).
