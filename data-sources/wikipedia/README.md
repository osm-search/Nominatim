# Wikipedia page data 

Convert [Wikipedia](https://dumps.wikimedia.org/) page data SQL dumps to postgreSQL files which can be imported into Nominatim database.

Processes data from whatever set of Wikipedia languages are specified. Processing the top 40 Wikipedia languages can take over a day, and will add nearly 1TB to the processing database. The 2 tables that will finally be imported into the Nominatim database will be 11GB and 2GB in size.

Replace '2019' with the current year throughout.

1. Create a new DB for processing
```CREATE DATABASE wikipedia2019
```

2. Download, convert, and import the data, then process summary statistics and compute importance scores
```cd data-sources/wikipedia 
./wikipedia_import.sh
```

3. Dump the two tables needed by nominatim database (will prompt for user password):
``` pg_dump -t wikipedia_article wikipedia2019 -U username -h localhost -W > wikipedia_article.sql
pg_dump -t wikipedia_redirect wikipedia2019 -U postgres -h localhost -W > wikipedia_redirect.sql
```

4. Import the two tables dumped above into nominatim DB. **Note:** If you have previous wikipedia tables make sure to first rename them.
``` cat wikipedia_article.sql | psql nominatim
cat wikipedia_redirect.sql | psql nominatim
```


