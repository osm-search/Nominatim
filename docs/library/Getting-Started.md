# Getting Started

The Nominatim search frontend can directly be used as a Python library in
scripts and applications. When you have imported your own Nominatim database,
then it is no longer necessary to run a full web service for it and access
the database through http requests. With the Nominatim library it is possible
to access all search functionality directly from your Python code. There are
also less constraints on the kinds of data that can be accessed. The library
allows to get access to more detailed information about the objects saved
in the database.

## Installation

To use the Nominatim library, you need access to a local Nominatim database.
Follow the [installation and import instructions](../admin/) to set up your
database.

!!! warning
    Access to the library is currently still experimental. It is not yet
    possible to install it in the usual way via pip or inside a virtualenv.
    To get access to the library you need to set an appropriate PYTHONPATH.
    With the default installation, the python library can be found under
    `/usr/local/share/nominatim/lib-python`. If you have installed Nominatim
    under a different prefix, adapt the `/usr/local/` part accordingly.
    You can also point the PYTHONPATH to the Nominatim source code.

    A proper installation as a Python library will follow in the next
    version.
