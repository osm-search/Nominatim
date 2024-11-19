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

The latest stable release can be downloaded from https://nominatim.org.
There you can also find [installation instructions for the release](https://nominatim.org/release-docs/latest/admin/Installation), as well as an extensive [Troubleshooting/FAQ section](https://nominatim.org/release-docs/latest/admin/Faq/).

[Detailed installation instructions for current master](https://nominatim.org/release-docs/develop/admin/Installation)
can be found at nominatim.org as well.

A quick summary of the necessary steps:

1. Create a Python virtualenv and install the packages:

        python3 -m venv nominatim-venv
        ./nominatim-venv/bin/pip install packaging/nominatim-{api,db}

2. Create a project directory, get OSM data and import:

        mkdir nominatim-project
        cd nominatim-project
        ../nominatim-venv/bin/nominatim import --osm-file <your planet file>

3. Start the webserver:

        ./nominatim-venv/bin/pip install uvicorn falcon
        ../nominatim-venv/bin/nominatim serve


License
=======

The Python source code is available under a GPL license version 3 or later.
The Lua configuration files for osm2pgsql are released under the
Apache License, Version 2.0. All other files are under a GPLv2 license.


Contributing
============

Contributions, bug reports and pull requests are welcome. When reporting a
bug, please use one of the
[issue templates](https://github.com/osm-search/Nominatim/issues/new/choose)
and make sure to provide all the information requested. If you are not
sure if you have really found a bug, please ask for help in the forums
first (see 'Questions' below).

For details on contributing, have a look at the
[contribution guide](CONTRIBUTING.md).


Questions and help
==================

If you have questions about search results and the OpenStreetMap data
used in the search, use the [OSM Forum](https://community.openstreetmap.org/).

For questions, community help and discussions around the software and
your own installation of Nominatim, use the
[Github discussions forum](https://github.com/osm-search/Nominatim/discussions).
