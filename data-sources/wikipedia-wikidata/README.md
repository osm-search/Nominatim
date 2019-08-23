## Add Wikipedia and Wikidata to Nominatim

OSM contributors frequently tag items with links to Wikipedia and Wikidata. Nominatim can use the page ranking of Wikipedia pages to help indicate the relative importance of osm features. This is done by calculating an importance score between 0 and 1 based on the number of inlinks to an article for a location. If two places have the same name and one is more important than the other, the wikipedia score often points to the correct place. 

These scripts extract and prepare both Wikipedia page rank and Wikidata links for use in Nominatim. Processing these data requires a large amount of disk space (~1TB) and considerable time (>24 hours).

Please note that if you have previous Wikipedia or Wikidata tables you should rename them before running these scripts.
  
