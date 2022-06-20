# Customizing Per-Country Data

Whenever an OSM is imported into Nominatim, the object is first assigned
a country. Nominatim can use this information to adapt various aspects of
the address computation to the local customs of the country. This section
explains how country assignment works and the principal per-country
localizations.

## Country assignment

Countries are assigned on the basis of country data from the OpenStreetMap
input data itself. Countries are expected to be tagged according to the
[administrative boundary schema](https://wiki.openstreetmap.org/wiki/Tag:boundary%3Dadministrative):
a OSM relation with `boundary=administrative` and `admin_level=2`. Nominatim
uses the country code to distinguish the countries.

If there is no country data available for a point, then Nominatim uses the
fallback data imported from `data/country_osm_grid.sql.gz`. This was computed
from OSM data as well but is guaranteed to cover all countries.

Some OSM objects may also be located outside any country, for example a buoy
in the middle of the ocean. These object do not get any country assigned and
get a default treatment when it comes to localized handling of data.

## Per-country settings

### Global country settings

The main place to configure settings per country is the file
`settings/country_settings.yaml`. This file has one section per country that
is recognised by Nominatim. Each section is tagged with the country code
(in lower case) and contains the different localization information. Only
countries which are listed in this file are taken into account for computations.

For example, the section for Andorra looks like this:

```
    partition: 35
    languages: ca
    names: !include country-names/ad.yaml
    postcode:
      pattern: "(ddd)"
      output: AD\1
```

The individual settings are described below.

#### `partition`

Nominatim internally splits the data into multiple tables to improve
performance. The partition number tells Nominatim into which table to put
the country. This is purely internal management and has no effect on the
output data.

The default is to have one partition per country.

#### `languages`

A comma-separated list of ISO-639 language codes of default languages in the
country. These are the languages used in name tags without a language suffix.
Note that this is not necessarily the same as the list of official languages
in the country. There may be officially recognised languages in a country
which are only ever used in name tags with the appropriate language suffixes.
Conversely, a non-official language may appear a lot in the name tags, for
example when used as an unofficial Lingua Franca.

List the languages in order of frequency of appearance with the most frequently
used language first. It is not recommended to add languages when there are only
very few occurrences.

If only one language is listed, then Nominatim will 'auto-complete' the
language of names without an explicit language-suffix.

#### `names`

List of names of the country and its translations. These names are used as
a baseline. It is always possible to search countries by the given names, no
matter what other names are in the OSM data. They are also used as a fallback
when a needed translation is not available.

!!! Note
    The list of names per country is currently fairly large because Nominatim
    supports translations in many languages per default. That is why the
    name lists have been separated out into extra files. You can find the
    name lists in the file `settings/country-names/<country code>.yaml`.
    The names section in the main country settings file only refers to these
    files via the special `!include` directive.

#### `postcode`

Describes the format of the postcode that is in use in the country.

When a country has no official postcodes, set this to no. Example:

```
ae:
    postcode: no
```

When a country has a postcode, you need to state the postcode pattern and
the default output format. Example:

```
bm:
    postcode:
      pattern: "(ll)[ -]?(dd)"
      output: \1 \2
```

The **pattern** is a regular expression that describes the possible formats
accepted as a postcode. The pattern follows the standard syntax for
[regular expressions in Python](https://docs.python.org/3/library/re.html#regular-expression-syntax)
with two extra shortcuts: `d` is a shortcut for a single digit([0-9])
and `l` for a single ASCII letter ([A-Z]).

Use match groups to indicate groups in the postcode that may optionally be
separated with a space or a hyphen.

For example, the postcode for Bermuda above always consists of two letters
and two digits. They may optionally be separated by a space or hyphen. That
means that Nominatim will consider `AB56`, `AB 56` and `AB-56` spelling variants
for one and the same postcode.

Never add the country code in front of the postcode pattern. Nominatim will
automatically accept variants with a country code prefix for all postcodes.

The **output** field is an optional field that describes what the canonical
spelling of the postcode should be. The format is the
[regular expression expand syntax](https://docs.python.org/3/library/re.html#re.Match.expand) referring back to the bracket groups in the pattern.

Most simple postcodes only have one spelling variant. In that case, the
**output** can be omitted. The postcode will simply be used as is.

In the Bermuda example above, the canonical spelling would be to have a space
between letters and digits.

!!! Warning
    When your postcode pattern covers multiple variants of the postcode, then
    you must explicitly state the canonical output or Nominatim will not
    handle the variations correctly.

### Other country-specific configuration

There are some other configuration files where you can set localized settings
according to the assigned country. These are:

 * [Place ranking configuration](Ranking.md)

Please see the linked documentation sections for more information.
