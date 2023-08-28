# Status

Report on the state of the service and database. Useful for checking if the
service is up and running. The JSON output also reports
when the database was last updated.

## Endpoint

The status API has the following format:

```
https://nominatim.openstreetmap.org/status
```

!!! danger "Deprecation warning"
    The API can also be used with the URL
    `https://nominatim.openstreetmap.org/status.php`. This is now deprecated
    and will be removed in future versions.


## Parameters

The status endpoint takes a single optional parameter:

| Parameter | Value | Default |
|-----------| ----- | ------- |
| format    | one of: `text`, `json` | 'text' |

Selects the output format. See below.


## Output

#### Text format

When everything is okay, a status code 200 is returned and a simple message: `OK`

On error it will return HTTP status code 500 and print a detailed error message, e.g.
`ERROR: Database connection failed`.



#### JSON format

Always returns a HTTP code 200, when the status call could be executed.

On success a JSON dictionary with the following structure is returned:

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

On error will return a shorter JSON dictionary with the error message
and status only, e.g.

```json
   {
       "status": 700,
       "message": "Database connection failed"
   }
```
