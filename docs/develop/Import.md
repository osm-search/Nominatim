# OSM Data Import

OSM data is initially imported using osm2pgsql. Nominatim uses its own data
output style 'gazetteer', which differs from the output style created for
map rendering.

## Database Layout

The gazetteer style produces a single table `place` with the following rows:

 * `osm_type` - kind of OSM object (**N** - node, **W** - way, **R** - relation)
 * `osm_id` - original OSM ID
 * `class` - key of principal tag defining the object type
 * `type` - value of principal tag defining the object type
 * `name` - collection of tags that contain a name or reference
 * `admin_level` - numerical value of the tagged administrative level
 * `address` - collection of tags defining the address of an object
 * `extratags` - collection of additional interesting tags that are not
                 directly relevant for searching
 * `geometry` - geometry of the object (in WGS84)

A single OSM object may appear multiple times in this table when it is tagged
with multiple tags that may constitute a principal tag. Take for example a
motorway bridge. In OSM, this would be a way which is tagged with
`highway=motorway` and `bridge=yes`. This way would appear in the `place` table
once with `class` of `highway` and once with a `class` of `bridge`. Thus the
*uique key* for `place` is (`osm_type`, `osm_id`, `class`).

## Configuring the Import

How tags are interpreted and assigned to the different `place` columns can be
configured via the import style configuration file (`CONST_Import_style`). This
is a JSON file which contains a list of rules which are matched against every
tag of every object and then assign the tag its specific role.

### Configuration Rules

A single rule looks like this:

```json
{
    "keys" : ["key1", "key2", ...],
    "values" : {
        "value1" : "prop",
        "value2" : "prop1,prop2"
    }
}
```

A rule first defines a list of keys to apply the rule to. This is always a list
of strings. The string may have four forms. An empty string matches against
any key. A string that ends in an asterisk `*` is a prefix match and accordingly
matches against any key that starts with the given string (minus the `*`). A
suffix match can be defined similarly with a string that starts with a `*`. Any
other string constitutes an exact match.

The second part of the rules defines a list of values and the properties that
apply to a successful match. Value strings may be either empty, which again
means that thy match against any value, or describe an exact match. Prefix
or suffix matching of values is not possible.

For a rule to match, it has to find a valid combination of keys and values. The
resulting property is that of the matched values.

The rules in a configuration file are processed sequentially and the first
match for each tag wins.

A rule where key and value are the empty string is special. This defines the
fallback when none of the rules matches. The fallback is always used as a last
resort when nothing else matches, no matter where the rule appears in the file.
Defining multiple fallback rules is not allowed. What happens in this case,
is undefined.

### Tag Properties

One or more of the following properties may be given for each tag:

* `main`

    A principal tag. A new row will be added for the object with key and value
    as `class` and `type`.

* `with_name`

    When the tag is a principal tag (`main` property set): only really add a new
    row, if there is any name tag found (a reference tag is not sufficient, see
    below).

* `with_name_key`

    When the tag is a principal tag (`main` property set): only really add a new
    row, if there is also a name tag that matches the key of the principal tag.
    For example, if the main tag is `bridge=yes`, then it will only be added as
    an extra row, if there is a tag `bridge:name[:XXX]` for the same object.
    If this property is set, all other names that are not domain-specific are
    ignored.

* `fallback`

    When the tag is a principal tag (`main` property set): only really add a new
    row, when no other principal tags for this object have been found. Only one
    fallback tag can win for an object.

* `operator`

    When the tag is a principal tag (`main` property set): also include the
    `operator` tag in the list of names. This is a special construct for an
    out-dated tagging practise in OSM. Fuel stations and chain restaurants
    in particular used to have the name of the chain tagged as `operator`.
    These days the chain can be more commonly found in the `brand` tag but
    there is still enough old data around to warrant this special case.

* `name`

    Add tag to the list of names.

* `ref`

    Add tag to the list of names as a reference. At the moment this only means
    that the object is not considered to be named for `with_name`.

* `address`

    At tag to the list of address tags. If the tag starts with `addr:` or
    `is_in:`, then this prefix is cut off before adding it to the list.

* `postcode`

    At the value as a postcode to the address tags. If multiple tags are
    candidate for postcodes, one wins out and the others are dropped.

* `country`

    At the value as a country code to the address tags. The value must be a
    two letter country code, otherwise it is ignored. If there are multiple
    tags that match, then one wins out and the others are dropped.

* `house`

    If no principle tags can be found for the object, still add the object with
    `class`=`place` and `type`=`house`. Use this for address nodes that have no
    other function.

* `interpolation`

    Add this object as an address interpolation (appears as `class`=`place` and
    `type`=`houses` in the database).

* `extra`

    Add tag to the list of extra tags.

* `skip`

    Skip the tag completely. Useful when a custom default fallback is defined
    or to define exceptions to rules.

A rule can define as many of these properties for one match as it likes. For
example, if the property is `"main,extra"` then the tag will open a new row
but also have the tag appear in the list of extra tags.

There are a number of pre-defined styles in the `settings/` directory. It is
advisable to start from one of these styles when defining your own.

### Changing the Style of Existing Databases

There is normally no issue changing the style of a database that is already
imported and now kept up-to-date with change files. Just be aware that any
change in the style applies to updates only. If you want to change the data
that is already in the database, then a reimport is necessary.
