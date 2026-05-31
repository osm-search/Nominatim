# Query preprocessing

The query preprocessing step allows to transform the incoming query before
it is processed by the tokenizer. This includes removing unrelated parts,
rephrasing and phrase tagging.

## Configuration

Query preprocessing is defined in the 'query_preprocessing.yaml' configuration
file. The file must contain a list of steps. Each step has a mandatory
parameter `step` which defines the type of preprocessor. Additional step
configuration may then be set with additional parameters.

The steps are executed in the order that they are defined in the configuration
file. Order matters here: each preprocessor works with the output of the previous
step.

## Pre-defined preprocessors

The following is a list of preprocessors that are shipped with Nominatim.
To learn how to define custom preprocessors, see the section on
[query processing modules](../develop/Query-Processing-Modules.md).

### split-japanese-phrases

::: nominatim_api.query_preprocessing.split_japanese_phrases
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

### regex-replace

::: nominatim_api.query_preprocessing.regex_replace
    options:
        members: False
        heading_level: 6
        docstring_section_style: spacy

