# Basic Architecture

Nominatim provides geocoding based on OpenStreetMap data. It uses a PostgreSQL
database as a backend for storing the data.

There are three basic parts to Nominatim's architecture: the data import,
the address computation and the search frontend.

The __data import__ stage reads the raw OSM data and extracts all information
that is useful for geocoding. This part is done by osm2pgsql, the same tool
that can also be used to import a rendering database. It uses the special
flex output style defined in the directory `/lib-lua`. The result of
the import can be found in the database table `place`.

The __address computation__ or __indexing__ stage takes the data from `place`
and adds additional information needed for geocoding. It ranks the places by
importance, links objects that belong together and computes addresses and
the search index. Most of this work is done in PL/pgSQL via database triggers
and can be found in the files in the `sql/functions/` directory.

The __search frontend__ implements the actual API. It takes search
and reverse geocoding queries from the user, looks up the data and
returns the results in the requested format. This part is located in the
`nominatim-api` package. The source code can be found in `src/nominatim_api`.
