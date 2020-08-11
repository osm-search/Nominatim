# Place Ranking in Nominatim

Nominatim uses two metrics to rank a place: search rank and address rank.
Both can be assigned a value between 0 and 30. They serve slightly
different purposes, which are explained in this chapter.

## Search rank

The search rank describes the extent and importance of a place. It is used
when ranking search result. Simply put, if there are two results for a
search query which are otherwise equal, then the result with the _lower_
search rank will be appear higher in the result list.

Search ranks are not so important these days because many well-known
places use the Wikipedia importance ranking instead.

The following table gives an overview of the kind of features that Nominatim
expects for each rank:

rank   | typical place types             | extent
-------|---------------------------------|-------
1-3    | oceans, continents              | -
4      | countries                       | -
5-9    | states, regions, provinces      | -
10-12  | counties                        | -
13-16  | cities, municipalities, islands | 7.5 km
17-18  | towns, boroughs                 | 4 km
19     | villages, suburbs               | 2 km
20     | hamlets, farms, neighbourhoods  |  1 km
21-25  | isolated dwellings, city blocks | 500 m

The extent column describes how far a feature is assumed to reach when it
is mapped only as a point. Larger features like countries and states are usually
available with their exact area in the OpenStreetMap data. That is why no extent
is given.

## Address rank

The address rank describes where a place shows up in an address hierarchy.
Usually only administrative boundaries and place nodes and areas are
eligible to be part of an address. Places that should not appear in the
address must have an address rank of 0.

The following table gives an overview how ranks are mapped to address parts:

 rank        | address part
-------------|-------------
 1-3         | _unused_
 4           | country
 5-9         | state
 10-12       | county
 13-16       | city
 17-21       | suburb
 22-25       | neighbourhood
 26-27       | street
 28-30       | POI/house number

The country rank 4 usually doesn't show up in the address parts of an object.
The country is determined indirectly from the country code.

Ranks 5-25 can be assigned more or less freely. They make up the major part
of the address.

The street ranks 26 and 27 are handled slightly differently. Only one object
from these ranks shows up in an address.

For POI level objects like shops, buildings or house numbers always use rank 30.
Ranks 28 is reserved for house number interpolations. 29 is for internal use
only.

## Rank configuration

Search and address ranks are assigned to a place when it is first imported
into the database. There are a few hard-coded rules for the assignment:

 * postcodes follow special rules according to their length
 * boundaries that are not areas and railway=rail are dropped completely
 * the following are always search rank 30 and address rank 0:
    * highway nodes
    * landuse that is not an area

Other than that, the ranks can be freely assigned via the JSON file
defined with `CONST_Address_Level_Config` according to their type and
the country they are in.

The address level configuration must consist of an array of configuration
entries, each containing a tag definition and an optional country array:

```
[ {
    "tags" : {
      "place" : {
        "county" : 12,
        "city" : 16,
      },
      "landuse" : {
        "residential" : 22,
        "" : 30
      }
    }
  },
  {
    "countries" : [ "ca", "us" ],
    "tags" : {
      "boundary" : {
        "administrative8" : 18,
        "administrative9" : 20
      },
      "landuse" : {
        "residential" : [22, 0]
      }
    }
  }
]
```

The `countries` field contains a list of countries (as ISO 3166-1 alpha 2 code)
for which the definition applies. When the field is omitted, then the
definition is used as a fallback, when nothing more specific for a given
country exists.

`tags` contains the ranks for key/value pairs. The ranks can be either a
single number, in which case they are the search and address rank, or an array
of search and address rank (in that order). The value may be left empty.
Then the rank is used when no more specific value is found for the given
key.

Countries and key/value combination may appear in multiple definitions. Just
make sure that each combination of country/key/value appears only once per
file. Otherwise the import will fail with a UNIQUE INDEX constraint violation
on import.

