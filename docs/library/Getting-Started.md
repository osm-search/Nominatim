# Getting Started

The Nominatim search frontend is implemented as a Python library and can as
such directly be used in Python scripts and applications. You don't need to
set up a web frontend and access it through HTTP calls. The library gives
direct access to the Nominatim database through similar search functions as
offered by the web API. In addition, it will give you a more complete and
detailed view on the search objects stored in the database.

!!! warning

    The Nominatim library is used for accessing a local Nominatim database.
    It is not meant to be used against web services of Nominatim like the
    one on https://nominatim.openstreetmap.org. If you need a Python library
    to access these web services, have a look at
    [GeoPy](https://geopy.readthedocs.io). Don't forget to consult the
    usage policy of the service you want to use before accessing such
    a web service.

## Installation

To use the Nominatim library, you need access to a local Nominatim database.
Follow the [installation](../admin/Installation.md) and
[import](../admin/Import.md) instructions to set up your database.

The Nominatim frontend library is contained in the Python package `nominatim-api`.
You can install the latest released version directly from pip:

    pip install nominatim-api

To install the package from the source tree directly, run:

    pip install packaging/nominatim-api

Usually you would want to run this in a virtual environment.

## A simple search example

To query the Nominatim database you need to first set up a connection. This
is done by creating an Nominatim API object. This object exposes all the
search functions of Nominatim that are also known from its web API.

This code snippet implements a simple search for the town of 'Brugge':

!!! example
    === "NominatimAPIAsync"
        ``` python
        import asyncio

        import nominatim_api as napi

        async def search(query):
            async with napi.NominatimAPIAsync() as api:
                return await api.search(query)

        results = asyncio.run(search('Brugge'))
        if not results:
            print('Cannot find Brugge')
        else:
            print(f'Found a place at {results[0].centroid.x},{results[0].centroid.y}')
        ```

    === "NominatimAPI"
        ``` python
        import nominatim_api as napi

        with napi.NominatimAPI() as api:
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

## Defining which database to use

The [Configuration](../admin/Import.md#configuration-setup-in-env)
section explains how Nominatim is configured using the
[dotenv](https://github.com/theskumar/python-dotenv) library.
The same configuration mechanism is used with the
Nominatim API library. You should therefore be sure you are familiar with
the section.

There are three different ways, how configuration options can be set for
a 'Nominatim API class'. When you have set up your Nominatim database, you
have normally created a [project directory](../admin/Import.md#creating-the-project-directory)
which stores the various configuration and customization files that Nominatim
needs. You may pass the location of the project directory to your
'Nominatim API class' constructor and it will read the .env file in the
directory and set the configuration accordingly. Here is the simple search
example, using the configuration from a pre-defined project directory in
`/srv/nominatim-project`:

!!! example
    === "NominatimAPIAsync"
        ``` python
        import asyncio

        import nominatim_api as napi

        async def search(query):
            async with napi.NominatimAPIAsync('/srv/nominatim-project') as api:
                return await api.search(query)

        results = asyncio.run(search('Brugge'))
        if not results:
            print('Cannot find Brugge')
        else:
            print(f'Found a place at {results[0].centroid.x},{results[0].centroid.y}')
        ```

    === "NominatimAPI"
        ``` python
        import nominatim_api as napi

        with napi.NominatimAPI('/srv/nominatim-project') as api:
            results = api.search('Brugge')

        if not results:
            print('Cannot find Brugge')
        else:
            print(f'Found a place at {results[0].centroid.x},{results[0].centroid.y}')
        ```


You may also configure Nominatim by setting environment variables.
Normally Nominatim will check the operating system environment. Lets
say you want to look up 'Brugge' in the special database named 'belgium' instead of the
standard 'nominatim' database. You can run the example script above like this:

```
NOMINATIM_DATABASE_DSN=pgsql:dbname=belgium python3 example.py
```

The third option to configure the library is to hand in the configuration
parameters into the 'Nominatim API class'. Changing the database would look
like this:

!!! example
    === "NominatimAPIAsync"
        ``` python
        import asyncio
        import nominatim_api as napi

        config_params = {
            'NOMINATIM_DATABASE_DSN': 'pgsql:dbname=belgium'
        }

        async def search(query):
            async with napi.NominatimAPIAsync(environ=config_params) as api:
                return await api.search(query)

        results = asyncio.run(search('Brugge'))
        ```

    === "NominatimAPI"
        ``` python
        import nominatim_api as napi

        config_params = {
            'NOMINATIM_DATABASE_DSN': 'pgsql:dbname=belgium'
        }

        with napi.NominatimAPI(environ=config_params) as api:
            results = api.search('Brugge')
        ```

When the `environ` parameter is given, then only configuration variables
from this dictionary will be used. The operating system's environment
variables will be ignored.

## Presenting results to humans

All search functions return full result objects from the database. Such a
result object contains lots of details: names, address information, OSM tags etc.
This gives you lots of flexibility what to do with the results.

One of the most common things to get is some kind of human-readable label
that describes the result in a compact form. Usually this would be the name
of the object and some parts of the address to explain where in the world
it is. To create such a label, you need two things:

* the address details of the place
* all names for the label adapted to the language you wish to use for display

Again searching for 'Brugge', this time with a nicely formatted result:

!!! example
    === "NominatimAPIAsync"
        ``` python
        import asyncio

        import nominatim_api as napi

        async def search(query):
            async with napi.NominatimAPIAsync() as api:
                return await api.search(query, address_details=True)

        results = asyncio.run(search('Brugge'))

        locale = napi.Locales(['fr', 'en'])
        for i, result in enumerate(results):
            address_parts = result.address_rows.localize(locale)
            print(f"{i + 1}. {', '.join(address_parts)}")
        ```

    === "NominatimAPI"
        ``` python
        import nominatim_api as napi

        with napi.NominatimAPI() as api:
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

The library has a helper class `Locales` which helps extracting a name of a
place in the preferred language. It takes a single parameter with a list
of language codes in the order of preference. So

``` python
locale = napi.Locales(['fr', 'en'])
```

creates a helper class that returns the name preferably in French. If that is
not possible, it tries English and eventually falls back to the default `name`
or `ref`.

The `Locales` object can be applied to a name dictionary to return the best-matching
name out of it:

``` python
>>> print(locale.display_name(results[0].names))
'Brugges'
```

The `address_row` field has a helper function to compute the display name for each Address Line
component based on its `local_name` field. This is then utilized by the overall `result` object,
which has a helper function to apply the function to all its ‘address_row’ members and saves
the result in the `locale_name` field. 

However, in order to set this `local_name` field in a preferred language, you must use the `Locales`
object which contains the function `localize_results`, which explicitly sets each `local_name field`.

``` python
>>> Locales().localize_results(results)
>>> address_parts = results[0].address_rows
>>> print(', '.join(address_parts))
Bruges, Flandre-Occidentale, Flandre, Belgique
```

This is a fairly simple way to create a human-readable description. The
place information in `address_rows` contains further information about each
place. For example, which OSM `admin_level` was used, what category the place
belongs to or what rank Nominatim has assigned. Use this to adapt the output
to local address formats.

For more information on address rows, see
[detailed address description](Result-Handling.md#detailed-address-description).
