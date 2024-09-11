# Low-level connections

The `NominatimAPIAsync` class allows to directly access the underlying
database connection to explore the raw data. Nominatim uses
[SQLAlchemy](https://docs.sqlalchemy.org/) for building queries. Please
refer to the documentation of the library to understand how to write SQL.

To get access to a search connection, use the `begin()` function of your
API object. This returns a `SearchConnection` object described below
wrapped in a context manager. Its
`t` property has definitions for all Nominatim search tables. For an
overview of available tables, refer to the
[Development Layout](../develop/Database-Layout.md) in in the development
chapter. Note that only tables that are needed for search are accessible
as SQLAlchemy tables.

!!! warning
    The database layout is not part of the API definition and may change
    without notice. If you play with the low-level access functions, you
    need to be prepared for such changes.

Here is a simple example, which prints how many places are available in
the placex table:

```
import asyncio
import sqlalchemy as sa
from nominatim_api import NominatimAPIAsync

async def print_table_size():
    api = NominatimAPIAsync()

    async with api.begin() as conn:
        cnt = await conn.scalar(sa.select(sa.func.count()).select_from(conn.t.placex))
        print(f'placex table has {cnt} rows.')

asyncio.run(print_table_size())
```

!!! warning
    Low-level connections may only be used to read data from the database.
    Do not use it to add or modify data or you might break Nominatim's
    normal functions.

## SearchConnection class

::: nominatim_api.SearchConnection
    options:
        members:
            - scalar
            - execute
            - get_class_table
            - get_db_property
            - get_property
        heading_level: 6
