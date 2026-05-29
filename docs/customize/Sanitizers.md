# Sanitizers

_Sanitizing_ is the process of cleaning up and otherwise preprocessing names
before adding them to the search index during the import process. This allows
to clean up tagging, normalise different spellings and mark names with extra
attributes for further processing.

!!! hint
    Sanitizers only have an effect on how the search index is built. They
    do not change the information about each place that is saved in the
    database. In particular, they have no influence on how the results are
    displayed. The returned results always show the original information as
    stored in the OpenStreetMap database.


## Configuration

The sanitizing process is defined in the 'sanitizers.yaml' configuration
file. The file must contain a list of steps. Each step has a mandatory
parameter `step` which defines the type of sanitizer. Additional step
configuration may then be set with additional parameters.

The steps are executed in the order that they are defined in the configuration
file. Order matters here: each sanitizer works with the output of the previous
step.

## Pre-defined sanitizers

The following is a list of sanitizers that are shipped with Nominatim.
To learn about how to add your own custom sanitizer, see the section on
[custom sanitizer modules](../develop/Sanitizer-Modules.md).

### affix-expansion

::: nominatim_db.tokenizer.sanitizers.affix_expansion
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### clean-housenumbers

::: nominatim_db.tokenizer.sanitizers.clean_housenumbers
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### clean-postcodes

::: nominatim_db.tokenizer.sanitizers.clean_postcodes
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### clean-tiger-tags

::: nominatim_db.tokenizer.sanitizers.clean_tiger_tags
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### delete-names

::: nominatim_db.tokenizer.sanitizers.delete_names
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### derive-names

::: nominatim_db.tokenizer.sanitizers.derive_names
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### split-name-list

::: nominatim_db.tokenizer.sanitizers.split_name_list
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### strip-brace-terms

::: nominatim_db.tokenizer.sanitizers.strip_brace_terms
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### tag-analyzer-by-language

::: nominatim_db.tokenizer.sanitizers.tag_analyzer_by_language
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### tag-japanese

::: nominatim_db.tokenizer.sanitizers.tag_japanese
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

