"""
Tests for the sanitizer that handles braced suffixes.
"""
import pytest

from nominatim.tokenizer.place_sanitizer import PlaceSanitizer
from nominatim.indexer.place_info import PlaceInfo

def run_sanitizer_on(**kwargs):
    place = PlaceInfo({'name': kwargs})
    name, _ = PlaceSanitizer([{'step': 'strip-brace-terms'}]).process_names(place)

    return sorted([(p.name, p.kind, p.suffix) for p in name])


def test_no_braces():
    assert run_sanitizer_on(name='foo', ref='23') == [('23', 'ref', None),
                                                      ('foo', 'name', None)]


def test_simple_braces():
    assert run_sanitizer_on(name='Halle (Saale)', ref='3')\
      == [('3', 'ref', None), ('Halle', 'name', None), ('Halle (Saale)', 'name', None)]
    assert run_sanitizer_on(name='ack ( bar')\
      == [('ack', 'name', None), ('ack ( bar', 'name', None)]


def test_only_braces():
    assert run_sanitizer_on(name='(maybe)') == [('(maybe)', 'name', None)]


def test_double_braces():
    assert run_sanitizer_on(name='a((b))') == [('a', 'name', None),
                                               ('a((b))', 'name', None)]
    assert run_sanitizer_on(name='a (b) (c)') == [('a', 'name', None),
                                                  ('a (b) (c)', 'name', None)]


def test_no_names():
    place = PlaceInfo({'address': {'housenumber': '3'}})
    name, address = PlaceSanitizer([{'step': 'strip-brace-terms'}]).process_names(place)

    assert not name
    assert len(address) == 1
