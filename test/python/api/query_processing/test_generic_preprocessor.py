import pytest

import nominatim_api.search.query as qmod
from nominatim_api.query_preprocessing.config import QueryConfig
from nominatim_api.query_preprocessing import generic_preprocessor


def create_test_config(replacements=None, replace_all=True, ignore_case=False):
    """Create a test configuration with predefined regex replacements."""
    config = QueryConfig()
    config.REGEX_REPLACE = {
        'replacements': replacements or [],
        'flags': {
            'replace_all': replace_all,
            'ignore_case': ignore_case
        }
    }
    return config


def test_basic_replacement():
    """Test simple text replacement."""
    config = create_test_config([
        {'pattern': 'foo', 'replace': 'bar'}
    ])
    proc = generic_preprocessor.create(config)

    query = [qmod.Phrase(qmod.PHRASE_ANY, "foo test foo")]
    result = proc(query)

    assert result == [qmod.Phrase(qmod.PHRASE_ANY, "bar test bar")]


def test_multiple_replacements():
    """Test multiple replacements applied in sequence."""
    config = create_test_config([
        {'pattern': 'foo', 'replace': 'bar'},
        {'pattern': 'bar', 'replace': 'baz'}
    ])
    proc = generic_preprocessor.create(config)

    query = [qmod.Phrase(qmod.PHRASE_ANY, "foo test foo")]
    result = proc(query)

    assert result == [qmod.Phrase(qmod.PHRASE_ANY, "baz test baz")]


def test_replace_once():
    """Test replacing only the first occurrence."""
    config = create_test_config([
        {'pattern': 'foo', 'replace': 'bar'}
    ], replace_all=False)
    proc = generic_preprocessor.create(config)

    query = [qmod.Phrase(qmod.PHRASE_ANY, "foo test foo")]
    result = proc(query)

    assert result == [qmod.Phrase(qmod.PHRASE_ANY, "bar test foo")]


def test_case_insensitive():
    """Test case-insensitive replacement."""
    config = create_test_config([
        {'pattern': 'foo', 'replace': 'bar'}
    ], ignore_case=True)
    proc = generic_preprocessor.create(config)

    query = [qmod.Phrase(qmod.PHRASE_ANY, "FOO test Foo")]
    result = proc(query)

    assert result == [qmod.Phrase(qmod.PHRASE_ANY, "bar test bar")]


def test_regex_groups():
    """Test replacement with regex groups."""
    config = create_test_config([
        {'pattern': '([a-z]+) *([a-z]+)', 'replace': r'\1\2'}
    ])
    proc = generic_preprocessor.create(config)

    query = [qmod.Phrase(qmod.PHRASE_ANY, "hello world")]
    result = proc(query)

    assert result == [qmod.Phrase(qmod.PHRASE_ANY, "helloworld")]


def test_empty_result_filtered():
    """Test that phrases becoming empty are filtered out."""
    config = create_test_config([
        {'pattern': '.*', 'replace': ''}
    ])
    proc = generic_preprocessor.create(config)

    query = [qmod.Phrase(qmod.PHRASE_ANY, "hello world")]
    result = proc(query)

    assert result == []


@pytest.mark.parametrize('inp,outp', [
    ('hello world', 'helloworld'),
    ('multiple   spaces', 'multiplespaces'),
    ('no-match', 'no-match')  # This won't match the pattern
])
def test_parametrized_cases(inp, outp):
    """Test multiple input/output pairs."""
    config = create_test_config([
        {'pattern': '([a-z]+) +([a-z]+)', 'replace': r'\1\2'}
    ])
    proc = generic_preprocessor.create(config)

    query = [qmod.Phrase(qmod.PHRASE_ANY, inp)]
    result = proc(query)

    if outp:
        assert result == [qmod.Phrase(qmod.PHRASE_ANY, outp)]
    else:
        assert result == []
