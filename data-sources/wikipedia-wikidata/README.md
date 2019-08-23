## Add Wikipedia and Wikidata to Nominatim

OSM contributors frequently tag items with links to Wikipedia and Wikidata. Nominatim can use the page ranking of Wikipedia pages to help indicate the relative importance of osm features. This is done by calculating an importance score between 0 and 1 based on the number of inlinks to an article for a location. If two places have the same name and one is more important than the other, the wikipedia score often points to the correct place. 

#### Create a new postgres DB for Processing

Due to the size of initial and intermediate tables, processing can be done in an external database:
```
CREATE DATABASE wikiprocessingdb
```
---
Wikipedia
---  

These scripts extract and prepare both Wikipedia page rank and Wikidata links for use in Nominatim. Processing these data requires a large amount of disk space (~1TB) and considerable time (>24 hours).

#### Import & Process Wikipedia data

This step downloads and converts [Wikipedia](https://dumps.wikimedia.org/) page data SQL dumps to postgreSQL files which can be imported and processed with pagelink information from Wikipedia language sites to calculate importance scores.

- The script will processes data from whatever set of Wikipedia languages are specified in the initial languages array. 

- Note that processing the top 40 Wikipedia languages can take over a day, and will add nearly 1TB to the processing database. The final output tables will be approximately 11GB and 2GB in size.

To download, convert, and import the data, then process summary statistics and compute importance scores, run:
```
./wikipedia_import.sh
```
---
Wikidata
---

This step downloads and converts [Wikidata](https://dumps.wikimedia.org/wikidatawiki/) page data SQL dumps to postgreSQL files which can be processed and imported into Nominatim database.

- Script processes data from whatever set of Wikipedia languages are specified. 
- Script presumes that the user has already processed Wikipedia tables as specified above. 

Wikidata processed here can then be used to enrich the wikipedia-articles table for improved Nominatim search results.

To download, convert, and import the data, then process required items, run:
``` 
cd data-sources/wikidata
./wikidata_import.sh
```

#### Step 3 - 
