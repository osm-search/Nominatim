# Getting Started

The Nominatim search frontend can directly be used as a Python library in
scripts and applications. When you have imported your own Nominatim database,
then it is no longer necessary to run a full web service for it and access
the database through http requests. There are
also less constraints on the kinds of data that can be accessed. The library
allows to get access to more detailed information about the objects saved
in the database.

!!! danger
    The library interface is currently in an experimental stage. There might
    be some smaller adjustments to the public interface until the next version.

    The library also misses a proper installation routine, so some manipulation
    of the PYTHONPATH is required. At the moment, use is only recommended for
    developers with some experience in Python.

## Installation

To use the Nominatim library, you need access to a local Nominatim database.
Follow the [installation](../admin/Installation.md) and
[import](../admin/Import.md) instructions to set up your database.

It is not yet possible to install it in the usual way via pip or inside a
virtualenv. To get access to the library you need to set an appropriate
`PYTHONPATH`. With the default installation, the python library can be found
under `/usr/local/share/nominatim/lib-python`. If you have installed
Nominatim under a different prefix, adapt the `/usr/local/` part accordingly.
You can also point the `PYTHONPATH` to the Nominatim source code.

### A simple search example

To query the Nominatim database you need to first set up a connection. This
is done by creating an Nominatim API object. This object exposes all the
search functions of Nominatim that are also known from its web API.

This code snippet implements a simple search for the town of 'Brugge':

!!! example
    === "NominatimAPIAsync"
        ``` python
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
            print(f'Found a place at {results[0].centroid.x},{results[0].centroid.y}')
        ```

    === "NominatimAPI"
        ``` python
        from pathlib import Path

        import nominatim.api as napi

        api = napi.NominatimAPI(Path('.'))

        results = api.search('Brugge')

        if not results:
            print('Cannot find Brugge')
        else:
            print(f'Found a place at {results[0].centroid.x},{results[0].centroid.y}')
        ```

The Nominatim library is designed around
[asyncio](https://docs.python.org/3/library/asyncio.html). `NominatimAPIAsync`
provides you with an interface of coroutines.
If you have many requests to make, coroutines can speed up your applications
significantly.

For smaller scripts there is also a synchronous wrapper around the API. By
using `NominatimAPI`, you get exactly the same interface using classic functions.

The examples in this chapter will always show-case both
implementations. The documentation itself will usually refer only to
'Nominatim API class' when both flavours are meant. If a functionality is
available only for the synchronous or asynchronous version, this will be
explicitly mentioned.

### Defining which database to use

The [Configuration](../admin/Import.md#configuration-setup-in-env)
section explains how Nominatim is configured using the
[dotenv](https://github.com/theskumar/python-dotenv) library.
The same configuration mechanism is used with the
Nominatim API library. You should therefore be sure you are familiar with
the section.

The constructor of the 'Nominatim API class' takes one mandatory parameter:
the path to the [project directory](../admin/Import.md#creating-the-project-directory).
You should have set up this directory as part of the Nominatim import.
Any configuration found in the `.env` file in this directory will automatically
used.

You may also configure Nominatim by setting environment variables.
Normally, Nominatim will check the operating system environment. This can be
overwritten by giving the constructor a dictionary of configuration parameters.

Let us look up 'Brugge' in the special database named 'belgium' instead of the
standard 'nominatim' database:

!!! example
    === "NominatimAPIAsync"
        ``` python
        from pathlib import Path
        import asyncio

        import nominatim.api as napi

        config_params = {
            'NOMINATIM_DATABASE_DSN': 'pgsql:dbname=belgium'
        }

        async def search(query):
            api = napi.NominatimAPIAsync(Path('.'), environ=config_params)

            return await api.search(query)

        results = asyncio.run(search('Brugge'))
        ```

    === "NominatimAPI"
        ``` python
        from pathlib import Path

        import nominatim.api as napi

        config_params = {
            'NOMINATIM_DATABASE_DSN': 'pgsql:dbname=belgium'
        }

        api = napi.NominatimAPI(Path('.'), environ=config_params)

        results = api.search('Brugge')
        ```

### Presenting results to humans

All search functions return the raw results from the database. There is no
full human-readable label. To create such a label, you need two things:

* the address details of the place
* adapt the result to the language you wish to use for display

Again searching for 'Brugge', this time with a nicely formatted result:

!!! example
    === "NominatimAPIAsync"
        ``` python
        from pathlib import Path
        import asyncio

        import nominatim.api as napi

        async def search(query):
            api = napi.NominatimAPIAsync(Path('.'))

            return await api.search(query, address_details=True)

        results = asyncio.run(search('Brugge'))

        locale = napi.Locales(['fr', 'en'])
        for i, result in enumerate(results):
            address_parts = result.address_rows.localize(locale)
            print(f"{i + 1}. {', '.join(address_parts)}")
        ```

    === "NominatimAPI"
        ``` python
        from pathlib import Path

        import nominatim.api as napi

        api = napi.NominatimAPI(Path('.'))

        results = api.search('Brugge', address_details=True)

        locale = napi.Locales(['fr', 'en'])
        for i, result in enumerate(results):
            address_parts = result.address_rows.localize(locale)
            print(f"{i + 1}. {', '.join(address_parts)}")
        ```

To request information about the address of a result, add the optional
parameter 'address_details' to your search:

``` python
>>> results = api.search('Brugge', address_details=True)
```

An additional field `address_rows` will set in results that are returned.
It contains a list of all places that make up the address of the place. For
simplicity, this includes name and house number of the place itself. With
the names in this list it is possible to create a human-readable description
of the result. To do that, you first need to decide in which language the
results should be presented. As with the names in the result itself, the
places in `address_rows` contain all possible name translation for each row.

The library has a helper class `Locale` which helps extracting a name of a
place in the preferred language. It takes a single parameter with a list
of language codes in the order of preference. So

``` python
locale = napi.Locale(['fr', 'en'])
```

creates a helper class that returns the name preferably in French. If that is
not possible, it tries English and eventually falls back to the default `name`
or `ref`.

The `Locale` object can be applied to a name dictionary to return the best-matching
name out of it:

``` python
>>> print(locale.display_name(results[0].names))
'Brugges'
```

The `address_row` field has a helper function to apply the function to all
its members and save the result in the `local_name` field. It also returns
all the localized names as a convenient simple list. This list can be used
to create a human-readable output:

``` python
>>> address_parts = results[0].address_rows.localize(locale)
>>> print(', '.join(address_parts))
Bruges, Flandre-Occidentale, Flandre, Belgique
```

This is a fairly simple way to create a human-readable description. The
place information in `address_rows` contains further information about each
place. For example, which OSM `adlin_level` was used, what category the place
belongs to or what rank Nominatim has assigned. Use this to adapt the output
to local address formats.

For more information on address rows, see
[detailed address description](Result-Handling.md#detailed-address-description).
