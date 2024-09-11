!!! Attention
    The current version of Nominatim implements two different search frontends:
    the old PHP frontend and the new Python frontend. They have a very similar
    API but differ in some implementation details. These are marked in the
    documentation as `[Python-only]` or `[PHP-only]`.

    `https://nominatim.openstreetmap.org` implements the **Python frontend**.
    So users should refer to the **`[Python-only]`** comments.

This section describes the API V1 of the Nominatim web service. The
service offers the following endpoints:

 * __[/search](Search.md)__ - search OSM objects by name or type
 * __[/reverse](Reverse.md)__ - search OSM object by their location
 * __[/lookup](Lookup.md)__ - look up address details for OSM objects by their ID
 * __[/status](Status.md)__ - query the status of the server
 * __/deletable__ - list objects that have been deleted in OSM but are held
                    back in Nominatim in case the deletion was accidental
 * __/polygons__ - list of broken polygons detected by Nominatim
 * __[/details](Details.md)__ - show internal details for an object (for debugging only)



