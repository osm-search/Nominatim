# Additional Data Sources

This guide explains how data sources other than OpenStreetMap mentioned in
the install instructions got obtained and converted.

## Country grid

Nominatim uses pre-generated country borders data. In case one imports only
a subset of a country. And to assign each place a partition. Nominatim
database tables are split into partitions for performance.

More details in [osm-search/country-grid-data](https://github.com/osm-search/country-grid-data).

## US Census TIGER

For the United States you can choose to import additional street-level data.
The data isn't mixed into OSM data but queried as fallback when no OSM
result can be found.

More details in [osm-search/TIGER-data](https://github.com/osm-search/TIGER-data).

## GB postcodes

For Great Britain you can choose to import Royalmail postcode centroids.

More details in [osm-search/gb-postcode-data](https://github.com/osm-search/gb-postcode-data).


## Wikipedia & Wikidata rankings

Nominatim can import "importance" data of place names. This greatly
improves ranking of results.

More details in [osm-search/wikipedia-wikidata](https://github.com/osm-search/wikipedia-wikidata).