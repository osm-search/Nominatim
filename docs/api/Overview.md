### Nominatim API

Nominatim indexes named (or numbered) features with the OSM data set and a subset of other unnamed features (pubs, hotels, churches, etc).

Its API has the following endpoints for querying the data:

 * __[/search](Search.md)__ - search OSM objects by name or type
 * __[/reverse](Reverse.md)__ - search OSM object by their location
 * __[/lookup](Lookup.md)__ - look up address details for OSM objects by thier ID
 * __/status__ - query the status of the server
 * __/deletable__ - list objects that have been deleted in OSM but are held
                    back in Nominatim in case the deletion was accidental
 * __/polygons__ - list of broken polygons detected by Nominatim
 * __/details__ - show internal details for an object (for debugging only)
