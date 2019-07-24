# Wikidata page data 

Convert [Wikidata](https://dumps.wikimedia.org/wikidatawiki/) page data SQL dumps to postgreSQL files which can be imported into Nominatim database.

Processes data from whatever set of Wikipedia languages are specified. Tresumes that the user has already [processed wikipedia data](../wikipedia/README.md). Wikidata processed here can then be used to enrich the wikipedia-articles table for improved Nominatim search results.

Replace '2019' with the current year throughout.

1. Create a new DB for processing wikidata
```CREATE DATABASE wikidata2019```

2. Download, convert, and import the data, then process required items
``` cd data-sources/wikidata
./wikidata_import.sh
```

3. Dump the table needed by nominatim database (will prompt for user password):
``` pg_dump -t wikidata_places wikidata2019 -U username -h localhost -W > wikidata_places.sql
```

4. Import the table dumped above into nominatim DB. **Note:** If you have a previous wikidata table make sure to first rename it.
``` cat wikidata_places.sql | psql nominatim
cat wikidata_places.sql | psql nominatim
```




