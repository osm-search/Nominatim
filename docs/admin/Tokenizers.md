# Tokenizers

The tokenizer module in Nominatim is responsible for analysing the names given
to OSM objects and the terms of an incoming query in order to make sure, they
can be matched appropriately.

Nominatim offers different tokenizer modules, which behave differently and have
different configuration options. This sections describes the tokenizers and how
they can be configured.

!!! important
    The use of a tokenizer is tied to a database installation. You need to choose
    and configure the tokenizer before starting the initial import. Once the import
    is done, you cannot switch to another tokenizer anymore. Reconfiguring the
    chosen tokenizer is very limited as well. See the comments in each tokenizer
    section.

## Legacy tokenizer

The legacy tokenizer implements the analysis algorithms of older Nominatim
versions. It uses a special Postgresql module to normalize names and queries.
This tokenizer is currently the default.

To enable the tokenizer add the following line to your project configuration:

```
NOMINATIM_TOKENIZER=legacy
```

The Postgresql module for the tokenizer is available in the `module` directory
and also installed with the remainder of the software under
`lib/nominatim/module/nominatim.so`. You can specify a custom location for
the module with

```
NOMINATIM_DATABASE_MODULE_PATH=<path to directory where nominatim.so resides>
```

This is in particular useful when the database runs on a different server.
See [Advanced installations](Advanced-Installations.md#importing-nominatim-to-an-external-postgresql-database) for details.

There are no other configuration options for the legacy tokenizer. All
normalization functions are hard-coded.

## ICU tokenizer

!!! danger
    This tokenizer is currently in active development and still subject
    to backwards-incompatible changes.

The ICU tokenizer uses the [ICU library](http://site.icu-project.org/) to
normalize names and queries. It also offers configurable decomposition and
abbreviation handling.

### How it works

On import the tokenizer processes names in the following four stages:

1. The **Normalization** part removes all non-relevant information from the
   input.
2. Incoming names are now converted to **full names**. This process is currently
   hard coded and mostly serves to handle name tags from OSM that contain
   multiple names (e.g. [Biel/Bienne](https://www.openstreetmap.org/node/240097197)).
3. Next the tokenizer creates **variants** from the full names. These variants
   cover decomposition and abbreviation handling. Variants are saved to the
   database, so that it is not necessary to create the variants for a search
   query.
4. The final **Tokenization** step converts the names to a simple ASCII form,
   potentially removing further spelling variants for better matching.

At query time only stage 1) and 4) are used. The query is normalized and
tokenized and the resulting string used for searching in the database.

### Configuration

The ICU tokenizer is configured using a YAML file which can be configured using
`NOMINATIM_TOKENIZER_CONFIG`. The configuration is read on import and then
saved as part of the internal database status. Later changes to the variable
have no effect.

Here is an example configuration file:

``` yaml
normalization:
    - ":: lower ()"
    - "ß > 'ss'" # German szet is unimbigiously equal to double ss
transliteration:
    - !include /etc/nominatim/icu-rules/extended-unicode-to-asccii.yaml
    - ":: Ascii ()"
variants:
    - language: de
      words:
        - ~haus => haus
        - ~strasse -> str
    - language: en
      words: 
        - road -> rd
        - bridge -> bdge,br,brdg,bri,brg
```

The configuration file contains three sections:
`normalization`, `transliteration`, `variants`.

The normalization and transliteration sections each must contain a list of
[ICU transformation rules](https://unicode-org.github.io/icu/userguide/transforms/general/rules.html).
The rules are applied in the order in which they appear in the file.
You can also include additional rules from external yaml file using the
`!include` tag. The included file must contain a valid YAML list of ICU rules
and may again include other files.

!!! warning
    The ICU rule syntax contains special characters that conflict with the
    YAML syntax. You should therefore always enclose the ICU rules in
    double-quotes.

The variants section defines lists of replacements which create alternative
spellings of a name. To create the variants, a name is scanned from left to
right and the longest matching replacement is applied until the end of the
string is reached.

The variants section must contain a list of replacement groups. Each group
defines a set of properties that describes where the replacements are
applicable. In addition, the word section defines the list of replacements
to be made. The basic replacement description is of the form:

```
<source>[,<source>[...]] => <target>[,<target>[...]]
```

The left side contains one or more `source` terms to be replaced. The right side
lists one or more replacements. Each source is replaced with each replacement
term.

!!! tip
    The source and target terms are internally normalized using the
    normalization rules given in the configuration. This ensures that the
    strings match as expected. In fact, it is better to use unnormalized
    words in the configuration because then it is possible to change the
    rules for normalization later without having to adapt the variant rules.

#### Decomposition

In its standard form, only full words match against the source. There
is a special notation to match the prefix and suffix of a word:

``` yaml
- ~strasse => str  # matches "strasse" as full word and in suffix position
- hinter~ => hntr  # matches "hinter" as full word and in prefix position
```

There is no facility to match a string in the middle of the word. The suffix
and prefix notation automatically trigger the decomposition mode: two variants
are created for each replacement, one with the replacement attached to the word
and one separate. So in above example, the tokenization of "hauptstrasse" will
create the variants "hauptstr" and "haupt str". Similarly, the name "rote strasse"
triggers the variants "rote str" and "rotestr". By having decomposition work
both ways, it is sufficient to create the variants at index time. The variant
rules are not applied at query time.

To avoid automatic decomposition, use the '|' notation:

``` yaml
- ~strasse |=> str
```

simply changes "hauptstrasse" to "hauptstr" and "rote strasse" to "rote str".

#### Initial and final terms

It is also possible to restrict replacements to the beginning and end of a
name:

``` yaml
- ^south => s  # matches only at the beginning of the name
- road$ => rd  # matches only at the end of the name
```

So the first example would trigger a replacement for "south 45th street" but
not for "the south beach restaurant".

#### Replacements vs. variants

The replacement syntax `source => target` works as a pure replacement. It changes
the name instead of creating a variant. To create an additional version, you'd
have to write `source => source,target`. As this is a frequent case, there is
a shortcut notation for it:

```
<source>[,<source>[...]] -> <target>[,<target>[...]]
```

The simple arrow causes an additional variant to be added. Note that
decomposition has an effect here on the source as well. So a rule

``` yaml
- "~strasse -> str"
```

means that for a word like `hauptstrasse` four variants are created:
`hauptstrasse`, `haupt strasse`, `hauptstr` and `haupt str`.

### Reconfiguration

Changing the configuration after the import is currently not possible, although
this feature may be added at a later time.
