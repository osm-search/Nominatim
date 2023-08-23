# Getting Started

The Nominatim search frontend can directly be used as a Python library in
scripts and applications. When you have imported your own Nominatim database,
then it is no longer necessary to run a full web service for it and access
the database through http requests. With the Nominatim library it is possible
to access all search functionality directly from your Python code. There are
also less constraints on the kinds of data that can be accessed. The library
allows to get access to more detailed information about the objects saved
in the database.

!!! danger
    The library interface is currently in an experimental stage. There might
    be some smaller adjustments to the public interface until the next version.

    The library also misses a proper installation routine, so some manipulation
    of the PYTHONPATH is required. Use is only recommended for advanced Python
    programmers at the moment.

## Installation

To use the Nominatim library, you need access to a local Nominatim database.
Follow the [installation and import instructions](../admin/) to set up your
database.

It is not yet possible to install it in the usual way via pip or inside a
virtualenv. To get access to the library you need to set an appropriate
PYTHONPATH. With the default installation, the python library can be found
under `/usr/local/share/nominatim/lib-python`. If you have installed
Nominatim under a different prefix, adapt the `/usr/local/` part accordingly.
You can also point the PYTHONPATH to the Nominatim source code.


### A simple search example

To query the Nominatim database you need to first set up a connection. This
is done by creating an Nominatim API object. This object exposes all the
search functions of Nominatim that are also knwon from its web API.

This code snippet implements a simple search for the town if 'Brugge':

=== "NominatimAPIAsync"
    ```
    from pathlib import Path
    import asyncio

    import nominatim.api as napi

    async def search(query):
        api = napi.NominatimAPIAsync(Path('.'))

        return await api.search(query)

    results = asyncio.run(search('Brugge'))
    if not results:
        print('Cannot find Brugge')
    else:
        print(f'Found a place at {results[0].centroid.x},{results[1].centroid.y}')
    ```

=== "NominatimAPI"
    ```
    from pathlib import Path

    import nominatim.api as napi

    api = napi.NominatimAPI(Path('.'))

    results = api.search('Brugge')

    if not results:
        print('Cannot find Brugge')
    else:
        print(f'Found a place at {results[0].centroid.x},{results[1].centroid.y}')
    ```

The Nonminatim API comes in two flavours: synchronous and asynchronous.
The complete Nominatim library is written so that it can work asynchronously.
If you have many requests to make, coroutines can speed up your applications
significantly.

For smaller scripts there is also a sychronous wrapper around the API.

### Defining which database to use


