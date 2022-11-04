# Status

Useful for checking if the service and database is running. The JSON output also shows
when the database was last updated.

## Parameters

* `format=[text|json]` (defaults to 'text')


## Output

#### Text format

```
   https://nominatim.openstreetmap.org/status.php
```

will return HTTP status code 200 and print `OK`.

On error it will return HTTP status code 500 and print a message, e.g.
`ERROR: Database connection failed`.



#### JSON format

```
   https://nominatim.openstreetmap.org/status.php?format=json
```

will return HTTP code 200 and a structure

```json
  {
      "status": 0,
      "message": "OK",
      "data_updated": "2020-05-04T14:47:00+00:00",
      "software_version": "3.6.0-0",
      "database_version": "3.6.0-0"
  }
```

The `software_version` field contains the version of Nominatim used to serve
the API. The `database_version` field contains the version of the data format
in the database.

On error will also return HTTP status code 200 and a structure with error
code and message, e.g.

```json
   {
       "status": 700,
       "message": "Database connection failed"
   }
```

Possible status codes are

  |     | message          | notes                                             |
-----|------------------|----------------------|---------------------------------------------------|
   | 700 | "No database"    | connection failed                                 |
   | 701 | "Module failed"  | database could not load nominatim.so              |
   | 702 | "Module call failed" | nominatim.so loaded but calling a function failed |
   | 703 | "Query failed"   | test query against a database table failed        |
   | 704 | "No value"       | test query worked but returned no results         |
   | 705 | "Import date is not available"           | No import dates were returned (enabling replication can fix this)         |