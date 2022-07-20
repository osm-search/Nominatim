## Configuring the Import

Which OSM objects are added to the database and which of the tags are used
can be configured via the import style configuration file. This
is a JSON file which contains a list of rules which are matched against every
tag of every object and then assign the tag its specific role.

The style to use is given by the `NOMINATIM_IMPORT_STYLE` configuration
option. There are a number of default styles, which are explained in detail
in the [Import section](../admin/Import.md#filtering-imported-data). These
standard styles may be referenced by their name.

You can also create your own custom style. Put the style file into your
project directory and then set `NOMINATIM_IMPORT_STYLE` to the name of the file.
It is always recommended to start with one of the standard styles and customize
those. You find the standard styles under the name `import-<stylename>.style`
in the standard Nominatim configuration path (usually `/etc/nominatim` or
`/usr/local/etc/nominatim`).

The remainder of the page describes the format of the file.

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
apply to a successful match. Value strings may be either empty, which
means that they match any value, or describe an exact match. Prefix
or suffix matching of values is not possible.

For a rule to match, it has to find a valid combination of keys and values. The
resulting property is that of the matched values.

The rules in a configuration file are processed sequentially and the first
match for each tag wins.

A rule where key and value are the empty string is special. This defines the
fallback when none of the rules match. The fallback is always used as a last
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

    Add tag to the list of address tags. If the tag starts with `addr:` or
    `is_in:`, then this prefix is cut off before adding it to the list.

* `postcode`

    Add the value as a postcode to the address tags. If multiple tags are
    candidate for postcodes, one wins out and the others are dropped.

* `country`

    Add the value as a country code to the address tags. The value must be a
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

### Changing the Style of Existing Databases

There is normally no issue changing the style of a database that is already
imported and now kept up-to-date with change files. Just be aware that any
change in the style applies to updates only. If you want to change the data
that is already in the database, then a reimport is necessary.
