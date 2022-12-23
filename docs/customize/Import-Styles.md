## Configuring the Import

In the very first step of a Nominatim import, OSM data is loaded into the
database. Nominatim uses [osm2pgsql](https://osm2pgsql.org) for this task.
It comes with a [flex style](https://osm2pgsql.org/doc/manual.html#the-flex-output)
specifically tailored to filter and convert OSM data into Nominatim's
internal data representation.

There are a number of default configurations for the flex style which
result in geocoding databases of different detail. The
[Import section](../admin/Import.md#filtering-imported-data) explains
these default configurations in detail.

You can also create your own custom style. Put the style file into your
project directory and then set `NOMINATIM_IMPORT_STYLE` to the name of the file.
It is always recommended to start with one of the standard styles and customize
those. You find the standard styles under the name `import-<stylename>.lua`
in the standard Nominatim configuration path (usually `/etc/nominatim` or
`/usr/local/etc/nominatim`).

The remainder of the page describes how the flex style works and how to
customize it.

### The `flex-base.lua` module

The core of Nominatim's flex import configuration is the `flex-base` module.
It defines the table layout used by Nominatim and provides standard
implementations for the import callbacks that make it easy to customize
how OSM tags are used by Nominatim.

Every custom style should include this module to make sure that the correct
tables are created. Thus start your custom style as follows:

``` lua
local flex = require('flex-base')

```

The following sections explain how the module can be customized.


### Changing the recognized tags

If you just want to change which OSM tags are recognized during import,
then there are a number of convenience functions to set the tag lists used
during the processing.

!!! warning
    There are no built-in defaults for the tag lists, so all the functions
    need to be called from your style script to fully process the data.
    Make sure you start from one of the default style and only modify
    the data you are interested in.

Many of the following functions take _key match lists_. These lists can
contain three kinds of strings to match against tag keys:
A string that ends in an asterisk `*` is a prefix match and accordingly matches
against any key that starts with the given string (minus the `*`). 
A suffix match can be defined similarly with a string that starts with a `*`.
Any other string is matched exactly against tag keys.


#### `set_main_tags()` - principal tags

If a principal or main tag is found on an OSM object, then the object
is included in Nominatim's search index. A single object may also have
multiple main tags. In that case, the object will be included multiple
times in the index, once for each main tag.

The flex script distinguishes between four types of main tags:

* __always__: a main tag that is used unconditionally
* __named__: consider this main tag only, if the object has a proper name
  (a reference is not enough, see below).
* __named_with_key__: consider this main tag only, when the object has
  a proper name with a domain prefix. For example, if the main tag is
  `bridge=yes`, then it will only be added as an extra row, if there is
  a tag `bridge:name[:XXX]` for the same object. If this property is set,
  all other names that are not domain-specific are ignored.
* __fallback__: use this main tag only, if there is no other main tag.
  Fallback always implied `named`, i.e. fallbacks are only tried for
  named objects.

The `set_main_tags()` function takes exactly one table parameter which
defines the keys and key/value combinations to include and the kind of
main tag. Each lua table key defines an OSM tag key. The value may
be a string defining the kind of main key as described above. Then the tag will
be considered a main tag for any possible value. To further restrict
which values are acceptable, give a table with the permitted values
and their kind of main tag. If the table contains a simple value without
key, then this is used as default for values that are not listed.

!!! example
    ``` lua
    flex.set_main_tags{
        boundary = {'administrative' = named},
        highway = {'always', street_lamp = 'named'}
        landuse = 'fallback',
    }
    ```

    In this example an object with a `boundary` tag will only be included
    when it has a value of `administrative`. Objects with `highway` tags are
    always included. However when the value is `street_lamp` then the object
    must have a name, too. With any other value, the object is included
    independently of the name. Finally, if a `landuse` tag is present then
    it will be used independely of the concrete value if neither boundary
    nor highway tags were found and the object is named.


#### `set_prefilters()` - ignoring tags

Pre-filtering of tags allows to ignore them for any further processing.
Thus pre-filtering takes precedence over any other tag processing. This is
useful when some specific key/value combinations need to be excluded from
processing. When tags are filtered, they may either be deleted completely
or moved to `extratags`. Extra tags are saved with the object and returned
to the user when requested, but are not used otherwise.

`set_prefilters()` takes a table with four optional fields:

* __delete_keys__ is a _key match list_ for tags that should be deleted
* __delete_tags__ contains a table of tag keys pointing to a list of tag
  values. Tags with matching key/value pairs are deleted.
* __extra_keys__ is a _key match list_ for tags which should be saved into
  extratags
* __delete_tags__ contains a table of tag keys pointing to a list of tag
  values. Tags with matching key/value pairs are moved to extratags.

Key list may contain three kinds of strings:
A string that ends in an asterisk `*` is a prefix match and accordingly matches
against any key that starts with the given string (minus the `*`). 
A suffix match can be defined similarly with a string that starts with a `*`.
Any other string is matched exactly against tag keys.

!!! example
    ``` lua
    flex.set_prefilters{
        delete_keys = {'source', 'source:*'},
        extra_tags = {'amenity' = {'yes', 'no'}
    }
    flex.set_main_tags{
        amenity = 'always'
    }
    ```

    In this example any tags `source` and tags that begin with `source:`  are
    deleted before any other processing is done. Getting rid of frequent tags
    this way can speed up the import.

    Tags with `amenity=yes` or `amenity=no` are moved to extratags. Later
    all tags with an `amenity` key are made a main tag. This effectively means
    that Nominatim will use all amenity tags except for those with value
    yes and no.

#### `set_name_tags()` - defining names

The flex script distinguishes between two kinds of names:

* __main__: the primary names make an object fully searchable.
  Main tags of type _named_ will only cause the object to be included when
  such a primary name is present. Primary names are usually those found
  in the `name` tag and its variants.
* __extra__: extra names are still added to the search index but they are
  alone not sufficient to make an object named.

`set_name_tags()` takes a table with two optional fields `main` and `extra`.
They take _key match lists_ for main and extra names respectively.

!!! example
    ``` lua
    flex.set_main_tags{'highway' = {'traffic_light' = 'named'}}
    flex.set_name_tags{main = {'name', 'name:*'},
                       extra = {'ref'}
                      }
    ```

    This example creates a search index over traffic lights but will
    only include those that have a common name and not those which just
    have some reference ID from the city.

#### `set_address_tags()` - defining address parts

Address tags will be used to build up the address of an object.

`set_address_tags()` takes a table with arbitrary fields pointing to
_key match lists_. To fields have a special meaning:

__main__ defines
the tags that make a full address object out of the OSM object. This
is usually the housenumber or variants thereof. If a main address tag
appears, then the object will always be included, if necessary with a
fallback of `place=house`. If the key has a prefix of `addr:` or `is_in:`
this will be stripped.

__extra__ defines all supplementary tags for addresses, tags like `addr:street`, `addr:city` etc. If the key has a prefix of `addr:` or `is_in:` this will be stripped.

All other fields will be handled as summary fields. If a key matches the
key match list, then its value will be added to the address tags with the
name of the field as key. If multiple tags match, then an arbitrary one
wins.

Country tags are handled slightly special. Only tags with a two-letter code
are accepted, all other values are discarded.

!!! example
    ``` lua
    flex.set_address_tags{
        main = {'addr:housenumber'},
        extra = {'addr:*'},
        postcode = {'postal_code', 'postcode', 'addr:postcode'},
        country = {'country-code', 'ISO3166-1'}
    }
    ```

    In this example all tags which begin with `addr:` will be saved in
    the address tag list. If one of the tags is `addr:housenumber`, the
    object will fall back to be entered as a `place=house` in the database
    unless there is another interested main tag to be found.

    Tags with keys `country-code` and `ISO3166-1` are saved with their
    value under `country` in the address tag list. The same thing happens
    to postcodes, they will always be saved under the key `postcode` thus
    normalizing the multitude of keys that are used in the OSM database.


#### `set_unused_handling()` - processing remaining tags

This function defines what to do with tags that remain after all tags
have been classified using the functions above. There are two ways in
which the function can be used:

`set_unused_handling(delete_keys = ..., delete_tags = ...)` deletes all
keys that match the descriptions in the parameters and moves all remaining
tags into the extratags list.
`set_unused_handling(extra_keys = ..., extra_tags = ...)` moves all tags
matching the parameters into the extratags list and then deletes the remaining
tags. For the format of the parameters see the description in `set_prefilters()`
above.

!!! example
    ``` lua
    flex.set_address_tags{
        main = {'addr:housenumber'},
        extra = {'addr:*', 'tiger:county'}
    }
    flex.set_unused_handling{delete_keys = {'tiger:*'}}
    ```

    In this example all remaining tags except those beginning with `tiger:`
    are moved to the extratags list. Note that it is not possible to
    already delete the tiger tags with `set_prefilters()` because that
    would remove tiger:county before the address tags are processed.

### Customizing osm2pgsql callbacks

osm2pgsql expects the flex style to implement three callbacks, one process
function per OSM type. If you want to implement special handling for
certain OSM types, you can override the default implementations provided
by the flex-base module.

#### Changing the relation types to be handled

The default scripts only allows relations of type `multipolygon`, `boundary`
and `waterway`. To add other types relations, set `RELATION_TYPES` for
the type to the kind of geometry that should be created. The following
kinds of geometries can be used:

* __relation_as_multipolygon__ creates a (Multi)Polygon from the ways in
  the relation. If the ways do not form a valid area, then the object is
  silently discarded.
* __relation_as_multiline__ creates a (Mutli)LineString from the ways in
  the relations. Ways are combined as much as possible without any regards
  to their order in the relation.

!!! Example
    ``` lua
    flex.RELATION_TYPES['site'] = flex.relation_as_multipolygon
    ```

    With this line relations of `type=site` will be included in the index
    according to main tags found. This only works when the site relation
    resolves to a valid area. Nodes in the site relation are not part of the
    geometry.


#### Adding additional logic to processing functions

The default processing functions are also exported by the flex-base module
as `process_node`, `process_way` and `process_relation`. These can be used
to implement your own processing functions with some additional processing
logic.

!!! Example
    ``` lua
    function osm2pgsql.process_relation(object)
        if object.tags.boundary ~= 'administrative' or object.tags.admin_level ~= '2' then
          flex.process_relation(object)
        end
    end
    ```

    This example discards all country-level boundaries and uses standard
    handling for everything else. This can be useful if you want to use
    your own custom country boundaries.


### Customizing the main processing function

The main processing function of the flex style can be found in the function
`process_tags`. This function is called for all OSM object kinds and is
responsible for filtering the tags and writing out the rows into Postgresql.

!!! Example
    ``` lua
    local original_process_tags = flex.process_tags

    function flex.process_tags(o)
        if o.object.tags.highway ~= nil and o.object.tags.access == 'no' then
            return
        end

        original_process_tags(o)
    end
    ```

    This example shows the most simple customization of the process_tags function.
    It simply adds some additional processing before running the original code.
    To do that, first save the original function and then overwrite process_tags
    from the module. In this example all highways which are not accessible
    by anyone will be ignored.


#### The `Place` class

The `process_tags` function receives a Lua object of `Place` type which comes
with some handy functions to collect the data necessary for geocoding and
writing it into the place table. Always use this object to fill the table.

The Place class has some attributes which you may access read-only:

* __object__ is the original OSM object data handed in by osm2pgsql
* __admin_level__ is the content of the admin_level tag, parsed into an
  integer and normalized to a value between 0 and 15
* __has_name__ is a boolean indicating if the object has a full name
* __names__ is a table with the collected list of name tags
* __address__ is a table with the collected list of address tags
* __extratags__ is a table with the collected list of additional tags to save

There are a number of functions to fill these fields. All functions expect
a table parameter with fields as indicated in the description.
Many of these functions expect match functions which are described in detail
further below.

* __delete{match=...}__ removes all tags that match the match function given
  in _match_.
* __grab_extratags{match=...}__ moves all tags that match the match function
  given in _match_ into extratags. Returns the number of tags moved.
* __clean{delete=..., extra=...}__ deletes all tags that match _delete_ and
  moves the ones that match _extra_  into extratags
* __grab_address_parts{groups=...}__ moves matching tags into the address table.
  _groups_ must be a group match function. Tags of the group `main` and
  `extra` are added to the address table as is but with `addr:` and `is_in:`
  prefixes removed from the tag key. All other groups are added with the
  group name as key and the value from the tag. Multiple values of the same
  group overwrite each other. The function returns the number of tags saved
  from the main group.
* __grab_main_parts{groups=...}__ moves matching tags into the name table.
  _groups_ must be a group match function. If a tags of the group `main` is
  present, the object will be marked as having a name. Tags of group `house`
  produce a fallback to `place=house`. This fallback is return by the function
  if present.

There are two functions to write a row into the place table. Both functions
expect the main tag (key and value) for the row and then use the collected
information from the name, address, extratags etc. fields to complete the row.
They also have a boolean parameter `save_extra_mains` which defines how any
unprocessed tags are handled: when True, the tags will be saved as extratags,
when False, they will be simply discarded.

* __write_row(key, value, save_extra_mains)__ creates a new table row from
  the current state of the Place object.
* __write_place(key, value, mtype, save_extra_mains)__ creates a new row
  conditionally. When value is nil, the function will attempt to look up the
  value in the object tags. If value is still nil or mtype is nil, the row
  is ignored. An mtype of `always` will then always write out the row,
  a mtype of `named` only, when the object has a full name. When mtype
  is `named_with_key`, the function checks for a domain name, i.e. a name
  tag prefixed with the name of the main key. Only if at least one is found,
  the row will be written. The names are replaced with the domain names found.

#### Match functions

The Place functions usually expect either a _match function_ or a
_group match function_ to find the tags to apply their function to.

The __match function__ is a Lua function which takes two parameters,
key and value, and returns a boolean to indicate that a tag matches. The
flex-base module has a convenience function `tag_match()` to create such a
function. It takes a table with two optional fields: `keys` takes a key match
list (see above), `tags` takes a table with keys that point to a list of
possible values, thus defining key/value matches.

The __group match function__ is a Lua function which also takes two parameters,
key and value, and returns a string indicating to which group or type they
belong to. The `tag_group()` can be used to create such a function. It expects
a table where the group names are the keys and the values are a key match list.



### Using the gazetteer output of osm2pgsql

Nominatim still allows you to configure the gazetteer output to remain
backwards compatible with older imports. It will be automatically used
when the style file name ends in `.style`. For documentation of the
old import style, please refer to the documentation of older releases
of Nominatim. Do not use the gazetteer output for new imports. There is no
guarantee that new versions of Nominatim are fully compatible with the
gazetteer output.

### Changing the Style of Existing Databases

There is normally no issue changing the style of a database that is already
imported and now kept up-to-date with change files. Just be aware that any
change in the style applies to updates only. If you want to change the data
that is already in the database, then a reimport is necessary.
