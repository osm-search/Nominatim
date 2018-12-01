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

## Address rank

The address rank describes where a place shows up in an address hierarchy.
Usually only administrative boundaries and place nodes and areas are
eligible to be part of an address. All other objects have an address rank
of 0.

Note that the search rank of a place place a role in the address computation
as well. When collecting the places that should make up the address parts
then only places are taken into account that have a lower address rank than
the search rank of the base object.

## Rank configuration

Search and address ranks are assigned to a place when it is first imported
into the database. There are a few hard-coded rules for the assignment:

 * postcodes follow special rules according to their length
 * boundaries that are not areas and railway=rail are dropped completely
 * the following are always search rank 30 and address rank 0:
    * highway nodes
    * landuse that is not an area

Other than that, the ranks can be freely assigned via the json file
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
single number, in which case they are to search and address rank, or a tuple
of search and address rank (in that order). The value may be left empty.
Then the rank is used when no more specific value is found for the given
key.

Countries and key/value combination may appear in multiple defintions. Just
make sure that each combination of counrty/key/value appears only once per
file. Otherwise the import will fail with a UNIQUE INDEX constraint violation
on import.
