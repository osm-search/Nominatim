# Configuring the Import of OSM data

In the very first step of a Nominatim import, OSM data is loaded into the
database. Nominatim uses [osm2pgsql](https://osm2pgsql.org) for this task.
It comes with a [flex style](https://osm2pgsql.org/doc/manual.html#the-flex-output)
specifically tailored to filter and convert OSM data into Nominatim's
internal data representation. Nominatim ships with a few preset
configurations for this import, each results in a geocoding database of
different detail. The
[Import section](../admin/Import.md#filtering-imported-data) explains
these default configurations in detail.

If you want to have more control over which OSM data is added to the database,
you can also create your own custom style. Create a new lua style file, put it
into your project directory and then set `NOMINATIM_IMPORT_STYLE` to the name
of the file. Custom style files can be used to modify the existing preset
configurations or to implement your own configuration from scratch.

The remainder of the page describes how the flex style works and how to
customize it.

## The `flex-base` lua module

The core of Nominatim's flex import configuration is the `flex-base` module.
It defines the table layout used by Nominatim and provides standard
implementations for the import callbacks that help with customizing
how OSM tags are used by Nominatim.

Every custom style must include this module to make sure that the correct
tables are created. Thus start your custom style as follows:

``` lua
local flex = require('flex-base')
```

### Using preset configurations

If you want to start with one of the existing presets, then you can import
its settings using the `load_topic()` function:

``` lua
local flex = require('flex-base')

flex.load_topic('streets')
```

The `load_topic` function takes an optional second configuration
parameter. The available options are explained in the
[themepark section](#using-osm2pgsql-themepark).

Available topics are: `admin`, `street`, `address`, `full`. These topic
correspond to the [import styles](../admin/Import.md#filtering-imported-data)
you can choose during import. To start with the 'extratags' style, use the
`full` topic with the appropriate config parameter:

``` lua
flex.load_topic('full', {with_extratags = true})
```

!!! note
    You can also directly import the preset style files, e.g.
    `local flex = require('import-street')`. It is not possible to
    set extra configuration this way.

### How processing works

When Nominatim processes an OSM object, it looks for four kinds of tags:
The _main tags_ classify what kind of place the OSM object represents. One
OSM object can have more than one main tag. In such case one database entry
is created for each main tag. _Name tags_ represent searchable names of the
place. _Address tags_ are used to compute the address hierarchy of the place.
Address tags are used for searching and for creating a display name of the place.
_Extra tags_ are any tags that are not directly related to search but
contain interesting additional information.

!!! danger
    Some tags in the extratags category are used by Nominatim to better
    classify the place. You want to make sure these are always present
    in custom styles.

Configuring the style means deciding which key and/or key/value is used
in which category.

## Changing the recognized tags

The flex style offers a number of functions to set the classification of
each OSM tag. Most of these functions can also take a preset string instead
of a tag description. These presets describe common configurations that
are also used in the definition of the predefined styles. This section
lists the configuration functions and the accepted presets.

#### Key match lists

Some of the following functions take _key match lists_. These lists can
contain three kinds of strings to match against tag keys:
A string that ends in an asterisk `*` is a prefix match and accordingly matches
against any key that starts with the given string (minus the `*`). 
A suffix match can be defined similarly with a string that starts with a `*`.
Any other string is matched exactly against tag keys.

###  Main tags

`set/modify_main_tags()` allow to define which tags are used as main tags. It
takes a lua table parameter which defines for keys and key/value
combinations, how they are classified.

The following classifications are recognized:

| classification  | meaning |
| :-------------- | :------ |
| always          | Unconditionally use this tag as a main tag. |
| named           | Consider as main tag, when the object has a primary name (see [names](#name-tags) below) |
| named_with_key  | Consider as main tag, when the object has a primary name with a domain prefix. For example, if the main tag is  `bridge=yes`, then it will only be added as an extra entry, if there is a tag `bridge:name[:XXX]` for the same object. If this property is set, all names that are not domain-specific are ignored. |
| fallback        | Consider as main tag only when no other main tag was found. Fallback always implies `named`, i.e. fallbacks are only tried for objects with primary names. |
| delete          | Completely ignore the tag in any further processing |
| extra           | Move the tag to extratags and then ignore it for further processing |
| `<function>`| Advanced handling, see [below](#advanced-main-tag-handling) |

Each key in the table parameter defines an OSM tag key. The value may
be directly a classification as described above. Then the tag will
be considered a main tag for any possible value that is not further defined.
To further restrict which values are acceptable, give a table with the
permitted values and their kind of main tag. If the table contains a simple
value without key, then this is used as default for values that are not listed.

`set_main_tags()` will completely replace the current main tag configuration
with the new configuration. `modify_main_tags()` will merge the new
configuration with the existing one. Otherwise, the two functions do exactly
the same.

!!! example
    ``` lua
    local flex = require('import-full')

    flex.set_main_tags{
        boundary = {administrative = 'named'},
        highway = {'always', street_lamp = 'named', no = 'delete'},
        landuse = 'fallback'
    }
    ```

    In this example an object with a `boundary` tag will only be included
    when it has a value of `administrative`. Objects with `highway` tags are
    always included with two exceptions: the troll tag `highway=no` is
    deleted on the spot. And when the value is `street_lamp` then the object
    must have a name, too. Finally, if a `landuse` tag is present then
    it will be used independently of the concrete value when neither boundary
    nor highway tags were found and the object is named.

##### Presets

| Name   | Description |
| :----- | :---------- |
| admin  | Basic tag set collecting places and administrative boundaries. This set is needed also to ensure proper address computation and should therefore always be present. You can disable selected place types like `place=locality` after adding this set, if they are not relevant for your use case. |
| all_boundaries | Extends the set of recognized boundaries and places to all available ones. |
| natural | Tags for natural features like rivers and mountain peaks. |
| street/default | Tags for streets. Major streets are always included, minor ones only when they have a name. |
| street/car | Tags for all streets that can be used by a motor vehicle. |
| street/all | Includes all highway features named and unnamed. |
| poi/delete | Adds most POI features with and without name. Some frequent but very domain-specific values are excluded by deleting them. |
| poi/extra | Like 'poi/delete' but excluded values are moved to extratags. |


##### Advanced main tag handling

The groups described above are in fact only a preset for a filtering function
that is used to make the final decision how a pre-selected main tag is entered
into Nominatim's internal table. To further customize handling you may also
supply your own filtering function.

The function takes up to three parameters: a Place object of the object
being processed, the key of the main tag and the value of the main tag.
The function may return one of three values:

* `nil` or `false` causes the entry to be ignored
* the Place object causes the place to be added as is
* `Place.copy(names=..., address=..., extratags=...) causes the
  place to be enter into the database but with name/address/extratags
  set to the given different values.

The Place object has some read-only values that can be used to determine
the handling:

* **object** is the original OSM object data handed in by osm2pgsql
* **admin_level** is the content of the admin_level tag, parsed into an integer and normalized to a value between 0 and 15
* **has_name** is a boolean indicating if the object has a primary name tag
* **names** is a table with the collected list of name tags
* **address** is a table with the collected list of address tags
* **extratags** is a table with the collected list of additional tags to save

!!! example
    ``` lua
    local flex = require('flex-base')

    flex.add_topic('street')

    local function no_sidewalks(place, k, v)
        if place.object.tags.footway == 'sidewalk' then
            return false
        end

        -- default behaviour is to have all footways
        return place
    end

    flex.modify_main_tags(highway = {'footway' = no_sidewalks}
    ```
    This script adds a custom handler for `highway=footway`. It only includes
    them in the database, when the object doesn't have a tag `footway=sidewalk`
    indicating that it is just part of a larger street which should already
    be indexed. Note that it is not necessary to check the key and value
    of the main tag because the function is only used for the specific
    main tag.


### Ignored tags

The function `ignore_keys()` sets the `delete` classification for keys.
This function takes a _key match list_ so that it is possible to exclude
groups of keys.

Note that full matches always take precedence over suffix matches, which
in turn take precedence over prefix matches.

!!! example
    ``` lua
    local flex = require('flex-base')

    flex.add_topic('admin')
    flex.ignore_keys{'old_name', 'old_name:*'}
    ```

    This example uses the `admin` preset with the exception that names
    that are no longer are in current use, are ignored.

##### Presets

| Name     | Description |
| :-----   | :---------- |
| metatags | Tags with meta information about the OSM tag like source, notes and import sources. |
| name     | Non-names that actually describe properties or name parts. These names can throw off search and should always be removed. |
| address  | Extra `addr:*` tags that are not useful for Nominatim. |


### Tags for `extratags`

The function `add_for_extratags()` sets the `extra` classification for keys.
This function takes a
_key match list_ so that it is possible to move groups of keys to extratags.

Note that full matches always take precedence over suffix matches, which
in turn take precedence over prefix matches.

!!! example
    ``` lua
    local flex = require('flex-base')

    flex.add_topic('street')
    flex.add_for_extratags{'surface', 'access', 'vehicle', 'maxspeed'}
    ```

    This example uses the `street` preset but adds a couple of tags that
    are of interest about the condition of the street.

##### Presets

| Name     | Description |
| :-----   | :---------- |
| required | Tags that Nominatim will use for various computations when present in extratags. Always include these. |

In addition, all [presets from ignored tags](#presets_1) are accepted.

### General pre-filtering

_(deprecated)_ `set_prefilters()` allows to set the `delete` and `extra`
classification for main tags.

This function removes all previously set main tags with `delete` and `extra`
classification and then adds the newly defined tags.

`set_prefilters()` takes a table with four optional fields:

* __delete_keys__ is a _key match list_ for tags that should be deleted
* __delete_tags__ contains a table of tag keys pointing to a list of tag
  values. Tags with matching key/value pairs are deleted.
* __extra_keys__ is a _key match list_ for tags which should be saved into
  extratags
* __extra_tags__ contains a table of tag keys pointing to a list of tag
  values. Tags with matching key/value pairs are moved to extratags.

!!! danger "Deprecation warning"
    Use of this function should be replaced with `modify_main_tags()` to
    set the data from `delete_tags` and `extra_tags`, with `ignore_keys()`
    for the `delete_keys` parameter and with `add_for_extratags()` for the
    `extra_keys` parameter.

### Name tags

`set/modify_name_tags()` allow to define the tags used for naming places. Name tags
can only be selected by their keys. The import script distinguishes
between primary and auxiliary names. A primary name is the given name of
a place. Having a primary name makes a place _named_. This is important
for main tags that are only included when a name is present. Auxiliary names
are identifiers like references. They may be searched for but should not
be included on their own.

The functions take a table with two optional fields `main` and `extra`.
They take _key match lists_ for primary and auxiliary names respectively.
A third field `house` can contain tags for names that appear in place of
house numbers in addresses. This field can only contain complete key names.
'house tags' are special in that they cause the OSM object to be added to
the database independently of the presence of other main tags.

`set_name_tags()` overwrites the current configuration, while
`modify_name_tags()` replaces the fields that are given. (Be aware that
the fields are replaced as a whole. `main = {'foo_name'}` will cause
`foo_name` to become the only recognized primary name. Any previously
defined primary names are forgotten.)

!!! example
    ``` lua
    local flex = require('flex-base')

    flex.set_main_tags{highway = {traffic_light = 'named'}}
    flex.set_name_tags{main = {'name', 'name:*'},
                       extra = {'ref'}
                      }
    ```

    This example creates a search index over traffic lights but will
    only include those that have a common name and not those which just
    have some reference ID from the city.

##### Presets

| Name     | Description |
| :-----   | :---------- |
| core     | Basic set of recognized names for all places. |
| address  | Additional names useful when indexing full addresses. |
| poi      | Extended set of recognized names for pois. Use on top of the core set. |

### Address tags

`set/modify_address_tags()` defines the tags that will be used to build
up the address of an object. Address tags can only be chosen by their key.

The functions take a table with arbitrary fields, each defining
a key list or _key match list_. Some fields have a special meaning:

| Field     | Type      | Description |
| :---------| :-------- | :-----------|
| main      | key list  | Tags that make a full address object out of the OSM object. This is usually the house number or variants thereof. If a main address tag appears, then the object will always be included, if necessary with a fallback of `place=house`. If the key has a prefix of `addr:` or `is_in:` this will be stripped. |
| extra     | key match list | Supplementary tags for addresses, tags like `addr:street`, `addr:city` etc. If the key has a prefix of `addr:` or `is_in:` this will be stripped. |
| interpolation | key list | Tags that identify address interpolation lines. |
| country   | key match list | Tags that may contain the country the place is in. The first found value with a two-letter code will be accepted, all other values are discarded. |
| _other_   | key match list | Summary field. If a key matches the key match list, then its value will be added to the address tags with the name of the field as key. If multiple tags match, then an arbitrary one wins. |

`set_address_tags()` overwrites the current configuration, while
`modify_address_tags()` replaces the fields that are given. (Be aware that
the fields are replaced as a whole.)

!!! example
    ``` lua
    local flex = require('import-full')

    flex.set_address_tags{
        main = {'addr:housenumber'},
        extra = {'addr:*'},
        postcode = {'postal_code', 'postcode', 'addr:postcode'},
        country = {'country_code', 'ISO3166-1'}
    }
    ```

    In this example all tags which begin with `addr:` will be saved in
    the address tag list. If one of the tags is `addr:housenumber`, the
    object will fall back to be entered as a `place=house` in the database
    unless there is another interested main tag to be found.

    Tags with keys `country_code` and `ISO3166-1` are saved with their
    value under `country` in the address tag list. The same thing happens
    to postcodes, they will always be saved under the key `postcode` thus
    normalizing the multitude of keys that are used in the OSM database.

##### Presets

| Name     | Description |
| :-----   | :---------- |
| core     | Basic set of tags needed to recognize address relationship for any place. Always include this. |
| houses   | Additional set of tags needed to recognize proper addresses |

### Handling of unclassified tags

`set_unused_handling()` defines what to do with tags that remain after all tags
have been classified using the functions above. There are two ways in
which the function can be used:

`set_unused_handling(delete_keys = ..., delete_tags = ...)` deletes all
keys that match the descriptions in the parameters and moves all remaining
tags into the extratags list.

`set_unused_handling(extra_keys = ..., extra_tags = ...)` moves all tags
matching the parameters into the extratags list and then deletes the remaining
tags. For the format of the parameters see the description in `set_prefilters()`
above.

When no special handling is set, then unused tags will be discarded with one
exception: place tags are kept in extratags for administrative boundaries.
When using a custom setting, you should also make sure that the place tag
is added for extratags.

!!! example
    ``` lua
    local flex = require('import-full')

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

## Customizing osm2pgsql callbacks

osm2pgsql expects the flex style to implement three callbacks, one process
function per OSM type. If you want to implement special handling for
certain OSM types, you can override the default implementations provided
by the flex-base module.

### Enabling additional relation types

OSM relations can represent very diverse
[types of real-world objects](https://wiki.openstreetmap.org/wiki/Key:type). To
be able to process them correctly, Nominatim needs to understand how to
create a geometry for each type. By default, the script knows how to
process relations of type `multipolygon`, `boundary` and `waterway`. All
other relation types are ignored.

To add other types relations, set `RELATION_TYPES` for
the type to the kind of geometry that should be created. The following
kinds of geometries can be used:

* __relation_as_multipolygon__ creates a (Multi)Polygon from the ways in
  the relation. If the ways do not form a valid area, then the object is
  silently discarded.
* __relation_as_multiline__ creates a (Multi)LineString from the ways in
  the relations. Ways are combined as much as possible without any regards
  to their order in the relation.

!!! Example
    ``` lua
    local flex = require('import-full')

    flex.RELATION_TYPES['site'] = flex.relation_as_multipolygon
    ```

    With this line relations of `type=site` will be included in the index
    according to main tags found. This only works when the site relation
    resolves to a valid area. Nodes in the site relation are not part of the
    geometry.


### Adding additional logic to processing functions

The default processing functions are also exported by the flex-base module
as `process_node`, `process_way` and `process_relation`. These can be used
to implement your own processing functions with some additional processing
logic.

!!! Example
    ``` lua
    local flex = require('import-full')

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

!!! danger "Deprecation Warning"
    The style used to allow overwriting the internal processing function
    `process_tags()`. While this is currently still possible, it is no longer
    encouraged and may stop working in future versions. The internal
    `Place` class should now be considered read-only.


## Using osm2pgsql-themepark

The Nominatim osm2pgsql style is designed so that it can also be used as
a theme for [osm2pgsql-themepark](https://osm2pgsql.org/themepark/). This
makes it easy to combine Nominatim with other projects like
[openstreetmap-carto](https://github.com/gravitystorm/openstreetmap-carto)
in the same database.

To set up one of the preset styles, simply include a topic with the same name:

```
local themepark = require('themepark')
themepark:add_topic('nominatim/address')
```

Themepark topics offer two configuration options:

* **street_theme** allows to choose one of the sub topics for streets:
    * _default_ - include all major streets and named minor paths
    * _car_ - include all streets physically usable by cars
    * _all_ - include all major streets and minor paths
* **with_extratags**, when set to a truthy value, then tags that are
  not specifically used for address or naming are added to the
  extratags column

The customization functions described in the
[Changing recognized tags](#changing-the-recognized-tags) section
are available from the theme. To access the theme you need to explicitly initialize it.

!!! Example
    ``` lua
    local themepark = require('themepark')

    themepark:add_topic('nominatim/full', {with_extratags = true})

    local flex = themepark:init_theme('nominatim')

    flex.modify_main_tags{'amenity' = {
                           'waste_basket' = 'delete'}
                      }
    ```
    This example uses the full Nominatim configuration but disables
    importing waste baskets.

You may also write a new configuration from scratch. Simply omit including
a Nominatim topic and only call the required customization functions.

Customizing the osm2pgsql processing functions as explained
[above](#adding-additional-logic-to-processing-functions) is not possible
when running under themepark. Instead include other topics that make the
necessary modifications or add an additional processor before including
the Nominatim topic.

!!! Example
    ``` lua
    local themepark = require('themepark')

    local function discard_country_boundaries(object)
        if object.tags.boundary == 'administrative' and object.tags.admin_level == '2' then
            return 'stop'
        end
    end

    themepark:add_proc('relation', discard_country_boundaries)
    -- Order matters here. The topic needs to be added after the custom callback.
    themepark:add_topic('nominatim/full', {with_extratags = true})
    ```
    Discarding country-level boundaries when running under themepark.

## Changing the style of existing databases

There is usually no issue changing the style of a database that is already
imported and now kept up-to-date with change files. Just be aware that any
change in the style applies to updates only. If you want to change the data
that is already in the database, then a reimport is necessary.
